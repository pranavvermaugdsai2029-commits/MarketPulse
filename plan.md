## Plan: MarketPulse End-Term Build (Ralphy Loop)

Goal: ship a high-scoring Problem 1 solution by first locking mandatory rubric coverage, then adding aggressive bonus features without destabilizing the demo.

Recommended Ralphy loop for every phase:
1. Run /gsd:discuss-phase
2. Run /gsd:research-phase
3. Run /gsd:plan-phase
4. Run /gsd:execute-phase
5. Run /gsd:verify-work
6. Run /gsd:progress

### Phase Plan (Day-by-Day)

1. Phase 0: Bootstrap and team operating model (Day 0)  
Outcome: repo initialized, environment baseline ready, owner split across 4 members, contribution policy set.

2. Phase 1: Architecture contract and HLD (Day 1-2, depends on Phase 0)  
Outcome: typed state contract finalized, node responsibilities frozen, conditional edge rules defined, one-page HLD ready for instructor review.

3. Phase 2: Data and schema foundation (Day 2-3, depends on Phase 1)  
Outcome: CSV-first reliable input pipeline, normalized data contracts, optional live adapters deferred behind flags.

4. Phase 3: Core LangGraph MVP (Day 4-6, depends on Phase 2)  
Outcome: LLM supervisor routing, at least 2 workers in parallel, aggregator merge, final brief writer, full node I/O logging.

5. Phase 4: Streamlit evaluator UX (Day 6-8, depends on Phase 3)  
Outcome: competitor toggles, run controls, final markdown output, sidebar visibility into worker outputs and dispatch reasoning.

6. Phase 5: Reliability and evaluation hardening (Day 8-10, depends on Phases 3-4)  
Outcome: failure handling, transition tests, and a 5-case evaluation suite for expected behavior checks.

7. Phase 6: Aggressive bonus track with safety gates (Day 9-11, depends on Phase 5)  
Outcome: weekly scheduler, week-over-week pricing delta detection, and 4th social listening worker, all behind feature toggles.

8. Phase 7: Demo and submission artifacts (Day 10-12, depends on Phases 5-6)  
Outcome: graph diagram artifact, 3-minute demo video, presentation PDF, business memo, complete README with citations.

9. Phase 8: Freeze and defense prep (Day 13, depends on Phase 7)  
Outcome: code freeze, full checklist pass, 8+2 timed rehearsal, all 4 members ready for architecture/implementation/business Q&A.

### Parallelization Map

1. Core graph and data contracts can progress in parallel only after state schema freeze.  
2. UI work starts once graph interfaces are stable.  
3. Bonus work runs only after MVP acceptance gate passes.  
4. Documentation and demo scripting can run in parallel with bonus testing.

### Acceptance Gates

1. Gate A: architecture approved and typed state frozen.  
2. Gate B: end-to-end graph works with required parallel fan-out.  
3. Gate C: UI exposes intermediate and final outputs clearly.  
4. Gate D: tests and failure scenarios pass.  
5. Gate E: bonus features do not break mandatory flow.  
6. Gate F: all deliverables complete before deadline.

### Locked Decisions

1. Topic: Problem 1 MarketPulse.  
2. LLM provider: Gemini.  
3. Data strategy: CSV-first reliability, live sources optional later.  
4. Bonus strategy: aggressive (scheduler + social worker + pricing delta).

