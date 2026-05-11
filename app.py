from __future__ import annotations

from pathlib import Path

import streamlit as st

from marketpulse.config import load_settings
from marketpulse.contracts import FeatureFlags, MarketPulseState
from marketpulse.data import filter_records, list_competitors, list_products, load_market_records
from marketpulse.evaluation import evaluate_state
from marketpulse.graph import MarketPulseWorkflow
from marketpulse.llm import create_brief_writer


def main() -> None:
    st.set_page_config(page_title="MarketPulse", layout="wide")
    settings = load_settings()

    st.title("MarketPulse")

    with st.sidebar:
        st.header("Run Setup")
        data_path = st.text_input("CSV path", value=str(settings.data_path))
        records = _load_records(Path(data_path))
        if not records:
            st.stop()

        product = st.selectbox("Product", list_products(records))
        competitors = st.multiselect(
            "Competitors",
            options=list_competitors(records),
            default=list_competitors(records)[:3],
        )
        question = st.text_area(
            "Business question",
            value="Which competitor moves should we react to this week?",
            height=90,
        )

        st.header("Feature Flags")
        enable_social_worker = st.toggle("Social listening worker", value=False)
        enable_pricing_delta = st.toggle("Week-over-week pricing delta", value=True)
        enable_weekly_scheduler = st.toggle("Weekly scheduler gate", value=False)
        run_button = st.button("Run MarketPulse", type="primary", use_container_width=True)

    selected_records = filter_records(records, competitors=competitors, product=product)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Rows", len(selected_records))
    metric_cols[1].metric("Competitors", len(competitors))
    metric_cols[2].metric("Product", product)
    metric_cols[3].metric("Gemini", "On" if settings.gemini_api_key else "Local")

    if not run_button:
        _render_data_preview(selected_records)
        return

    if len(selected_records) == 0:
        st.error("No records match the selected filters.")
        return

    state = MarketPulseState(
        question=question,
        competitors=competitors,
        records=selected_records,
        feature_flags=FeatureFlags(
            enable_social_worker=enable_social_worker,
            enable_pricing_delta=enable_pricing_delta,
            enable_weekly_scheduler=enable_weekly_scheduler,
        ),
    )
    writer = create_brief_writer(settings.gemini_api_key, settings.model_name)
    workflow = MarketPulseWorkflow(brief_writer=writer)

    with st.spinner("Running supervisor, workers, aggregator, and brief writer..."):
        completed = workflow.run(state)

    _render_results(completed, workflow)


def _load_records(path: Path):
    try:
        return load_market_records(path)
    except Exception as exc:
        st.error(f"Could not load market data: {exc}")
        return []


def _render_data_preview(records) -> None:
    st.subheader("Selected Data Preview")
    rows = [
        {
            "week_start": record.week_start.isoformat(),
            "competitor": record.competitor,
            "product": record.product,
            "price": record.price,
            "promo": record.promo,
            "traffic_index": record.traffic_index,
            "review_score": record.review_score,
            "social_mentions": record.social_mentions,
            "social_sentiment": record.social_sentiment,
        }
        for record in records
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_results(state: MarketPulseState, workflow: MarketPulseWorkflow) -> None:
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.subheader("Final Markdown Output")
        st.markdown(state.final_brief)

    with right:
        st.subheader("Dispatch Reasoning")
        if state.supervisor_decision:
            st.write(state.supervisor_decision.reasoning)
            st.caption("Conditional edge rules")
            for worker, rule in workflow.describe_edges().items():
                st.write(f"**{worker}:** {rule}")

        st.subheader("Acceptance Checks")
        for result in evaluate_state(state):
            st.write(f"{'PASS' if result.passed else 'FAIL'}: {result.name}")
            st.caption(result.detail)

    st.subheader("Worker Outputs")
    tabs = st.tabs([output.title for output in state.worker_outputs.values()])
    for tab, output in zip(tabs, state.worker_outputs.values(), strict=True):
        with tab:
            st.write(output.summary)
            st.json(output.metrics)
            for bullet in output.bullets:
                st.write(f"- {bullet}")

    st.subheader("Node I/O Log")
    st.dataframe(
        [
            {
                "timestamp": log.timestamp,
                "node": log.node,
                "event": log.event,
                "metadata": log.metadata,
            }
            for log in state.logs
        ],
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
