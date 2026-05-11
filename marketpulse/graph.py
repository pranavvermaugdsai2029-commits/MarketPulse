"""Graph-style orchestration for the MarketPulse agent workflow."""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, TypedDict

from marketpulse.agents import (
    EDGE_RULES,
    aggregate_outputs,
    create_pricing_data,
    create_promo_data,
    create_sentiment_data,
    route_workers,
    run_worker,
)
from marketpulse.contracts import MarketPulseState, WorkerName, WorkerOutput
from marketpulse.llm import BriefWriter, LocalBriefWriter

# Phase 6: Import social data creation
from marketpulse.social_listening import create_social_data


class _GraphPayload(TypedDict):
    state: MarketPulseState


class MarketPulseWorkflow:
    """Executes the supervisor, parallel workers, aggregator, and brief writer."""

    def __init__(self, brief_writer: BriefWriter | None = None) -> None:
        self.brief_writer = brief_writer or LocalBriefWriter()
        self._compiled_graph = self._compile_langgraph()

    def run(self, state: MarketPulseState) -> MarketPulseState:
        if self._compiled_graph is not None:
            result = self._compiled_graph.invoke({"state": state})
            return result["state"]

        return self._run_direct(state)

    def _run_direct(self, state: MarketPulseState) -> MarketPulseState:
        self._supervise(state)
        self._run_workers(state)
        self._aggregate(state)
        self._populate_structured_data(state)
        self._write_brief(state)
        return state

    def describe_edges(self) -> dict[WorkerName, str]:
        return dict(EDGE_RULES)

    def _compile_langgraph(self) -> Any | None:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Core Pydantic V1 functionality isn't compatible.*",
                    category=UserWarning,
                )
                from langgraph.graph import END, START, StateGraph
        except ImportError:
            return None

        graph = StateGraph(_GraphPayload)
        graph.add_node("supervisor", self._langgraph_supervisor)
        graph.add_node("parallel_workers", self._langgraph_parallel_workers)
        graph.add_node("aggregator", self._langgraph_aggregator)
        graph.add_node("structured_data", self._langgraph_structured_data)
        graph.add_node("brief_writer", self._langgraph_brief_writer)
        graph.add_edge(START, "supervisor")
        graph.add_edge("supervisor", "parallel_workers")
        graph.add_edge("parallel_workers", "aggregator")
        graph.add_edge("aggregator", "structured_data")
        graph.add_edge("structured_data", "brief_writer")
        graph.add_edge("brief_writer", END)
        return graph.compile()

    def _langgraph_supervisor(self, payload: _GraphPayload) -> _GraphPayload:
        self._supervise(payload["state"])
        return payload

    def _langgraph_parallel_workers(self, payload: _GraphPayload) -> _GraphPayload:
        self._run_workers(payload["state"])
        return payload

    def _langgraph_aggregator(self, payload: _GraphPayload) -> _GraphPayload:
        self._aggregate(payload["state"])
        return payload

    def _langgraph_structured_data(self, payload: _GraphPayload) -> _GraphPayload:
        self._populate_structured_data(payload["state"])
        return payload

    def _langgraph_brief_writer(self, payload: _GraphPayload) -> _GraphPayload:
        self._write_brief(payload["state"])
        return payload

    def _supervise(self, state: MarketPulseState) -> None:
        """Run LLM-based supervisor for intelligent worker routing."""
        state.add_log("supervisor", "started", competitors=state.competitors)
        state.supervisor_decision = route_workers(state.records, state.feature_flags)
        state.add_log(
            "supervisor",
            "completed",
            selected_workers=state.supervisor_decision.selected_workers,
            skipped_workers=state.supervisor_decision.skipped_workers,
        )

    def _run_workers(self, state: MarketPulseState) -> None:
        """Run selected workers in parallel."""
        if state.supervisor_decision is None:
            raise RuntimeError("Supervisor must run before worker dispatch.")

        selected = state.supervisor_decision.selected_workers
        if len(selected) < 2:
            raise RuntimeError("At least two workers are required for MVP parallel fan-out.")

        state.add_log("workers", "dispatch_started", selected_workers=selected)
        max_workers = min(len(selected), 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_worker, worker, state.records, state.feature_flags): worker
                for worker in selected
            }
            for future in as_completed(futures):
                worker = futures[future]
                output = future.result()
                state.worker_outputs[worker] = output
                state.add_log("workers", "worker_completed", worker=worker)

        state.worker_outputs = _ordered_outputs(state.worker_outputs, selected)
        state.add_log("workers", "dispatch_completed", completed_workers=list(state.worker_outputs))

    def _aggregate(self, state: MarketPulseState) -> None:
        """Aggregate worker outputs into consolidated insights."""
        state.add_log("aggregator", "started", worker_count=len(state.worker_outputs))
        state.aggregated = aggregate_outputs(state.worker_outputs)
        state.add_log(
            "aggregator",
            "completed",
            risks=len(state.aggregated.risks),
            opportunities=len(state.aggregated.opportunities),
        )

    def _populate_structured_data(self, state: MarketPulseState) -> None:
        """Populate structured data fields from worker outputs."""
        state.add_log("structured_data", "started")

        # Create structured data from worker outputs
        state.pricing_data = create_pricing_data(state.records, state.worker_outputs)
        state.sentiment_data = create_sentiment_data(state.records, state.worker_outputs)
        state.promo_data = create_promo_data(state.records, state.worker_outputs)

        # Phase 6: Create social data if social worker ran
        if "social" in state.worker_outputs:
            state.social_data = create_social_data(state.worker_outputs["social"])

        # Create structured brief
        if state.aggregated and state.supervisor_decision:
            from marketpulse.contracts import FinalBrief

            worker_findings = []
            for output in state.worker_outputs.values():
                worker_findings.append({
                    "worker": output.worker,
                    "title": output.title,
                    "summary": output.summary,
                    "bullets": output.bullets,
                    "metrics": output.metrics,
                    "confidence": output.confidence,
                })

            state.structured_brief = FinalBrief(
                title="MarketPulse Competitive Brief",
                run_id=state.run_id,
                question=state.question,
                competitors=state.competitors,
                dispatch_reasoning=state.supervisor_decision.reasoning,
                executive_summary=state.aggregated.executive_summary,
                worker_findings=worker_findings,
                opportunities=state.aggregated.opportunities,
                risks=state.aggregated.risks,
                recommended_actions=state.aggregated.recommended_actions,
                node_logs=[{"timestamp": log.timestamp, "node": log.node, "event": log.event} for log in state.logs],
            )

        state.add_log("structured_data", "completed")

    def _write_brief(self, state: MarketPulseState) -> None:
        """Generate final markdown brief."""
        if state.aggregated is None or state.supervisor_decision is None:
            raise RuntimeError("Aggregation and supervisor decision are required before brief writing.")

        # Use structured brief if available, otherwise fall back to legacy format
        if state.structured_brief:
            state.final_brief = state.to_markdown_brief()
        else:
            prompt = _build_markdown_brief(state)
            state.final_brief = self.brief_writer.generate(prompt)

        state.add_log("brief_writer", "completed", character_count=len(state.final_brief))


def _ordered_outputs(
    outputs: dict[WorkerName, WorkerOutput],
    selected: list[WorkerName],
) -> dict[WorkerName, WorkerOutput]:
    """Order worker outputs according to selection order."""
    return {worker: outputs[worker] for worker in selected if worker in outputs}


def _build_markdown_brief(state: MarketPulseState) -> str:
    """Build markdown brief from state (legacy format for backward compatibility)."""
    assert state.aggregated is not None
    assert state.supervisor_decision is not None

    lines = [
        "# MarketPulse Competitive Brief",
        "",
        f"**Run ID:** `{state.run_id}`",
        f"**Question:** {state.question}",
        f"**Competitors:** {', '.join(state.competitors)}",
        "",
        "## Dispatch Reasoning",
        "",
        state.supervisor_decision.reasoning,
        "",
        "## Executive Summary",
        "",
        state.aggregated.executive_summary,
        "",
        "## Worker Findings",
        "",
    ]

    for output in state.worker_outputs.values():
        lines.extend([f"### {output.title}", "", output.summary, ""])
        lines.extend(f"- {bullet}" for bullet in output.bullets)
        lines.append("")

    lines.extend(["## Opportunities", ""])
    lines.extend(f"- {item}" for item in state.aggregated.opportunities)
    lines.extend(["", "## Risks", ""])
    lines.extend(f"- {item}" for item in state.aggregated.risks)
    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {item}" for item in state.aggregated.recommended_actions)
    lines.extend(["", "## Node I/O Log", ""])
    lines.extend(f"- `{log.timestamp}` `{log.node}` {log.event}" for log in state.logs)

    return "\n".join(lines).strip() + "\n"
