# V5.2 Phase 2B Checkpoint 18 hard stop — 2026-09-24

## Decision

```text
CHECKPOINT 18 = FAIL / STOP AT TASK 12
TASKS 5-9 = IMPLEMENTED, NOT BROADLY ACCEPTED
TASK 10 = PROVISIONAL CODE, SEMANTIC GATES NOT ESTABLISHED
TASK 11 = STATIC FIREWALL TESTED
TASK 12 = NO FORMAL PILOT PREREGISTRATION
CHECKPOINT 19 PILOT = NOT RUN
CHECKPOINT 20 BROAD MATERIALIZATION = NOT RUN
CHECKPOINT 21 FINAL ACCEPTANCE = NOT RUN
PHASE 2B = PENDING
PHASE 3 = BLOCKED / NOT STARTED
```

The Checkpoint 18 PASS conditions cannot be reconstructed from the current
runtime. Do not treat the green unit suite as pilot or broad historical
acceptance.

## Blocker 1 — no production five-domain month evidence producer

`HistoricalLabelEvidenceAssemblerV1.assemble()` accepts a caller-supplied
`HistoricalEvidenceWindowV1`; `materialize_anchor()` requires that window and
an assembler; `materialize_month()` requires a caller-supplied `rows` iterable.
No production path currently reads arbitrary anchors from the exact approved
calendar, master/identity, daily-bar composite, historical-status, and
corporate-action artifacts into a bounded month index and then emits those
windows. The real integration regression rebuilds a window from the frozen
Phase 2A slot assembler. That is a useful equivalence check, but the slot
assembler is not an arbitrary-anchor production source.

Read-only reproduction:

```text
python -c "import inspect; from v5_2.labels.materializer import materialize_month,materialize_anchor; print(inspect.signature(materialize_month)); print(inspect.signature(materialize_anchor))"
MONTH_SIGNATURE = (root, month, lineage_ids, version, *, rows)
ANCHOR_SIGNATURE = (root, anchor, lineage, version, *, assembler=None, evidence_window=None, latest_completed_session=None)
```

This blocks a real source-pinned candidate census and a truthful Task 12
preregistration ID. It also blocks the pilot and broad historical run. The
bridge design explicitly requires read-only, exact-pinned calendar, identity,
bar, status, and CA interval indexes built once per lineage/month.

## Blocker 2 — 18-gate evaluator accepts ungrounded equal hashes

`GatePredicateEvidenceV1` currently takes caller-provided `expected_hash` and
`observed_hash`. For thirteen semantic/operational gates, the evaluator only
checks that the two strings are equal. It does not independently derive return,
MFE/MAE, barrier, CA, suspension, delisting, identity, replay, idempotency, or
clean-room outcomes from pinned input artifacts. The five structural gates
have additional checks, but this does not establish 18/18 acceptance.

Read-only reproduction:

```text
python -c "from tests.labels.test_phase2b_gates import gate_fixture; from v5_2.labels.phase2b_gates import evaluate_phase2b_gates; x=gate_fixture(); y=evaluate_phase2b_gates(x); print(y.all_pass); print(next(z.status for z in y.results if z.gate=='RETURN_SEMANTICS')); print(next(z.status for z in y.results if z.gate=='BARRIER_SEMANTICS'))"
True
PASS
PASS
```

The fixture supplies synthetic equal hashes rather than an independently
recomputed market-data comparison. Those PASS values prove only the current
code path; they cannot be used as formal predicate evidence. A formal gate
input must bind exact artifacts, independent expected semantics, observed
results, and the producer/version of each comparison. In particular, a
count-preserving barrier/H5 scheduling error must fail the barrier gate even
when a caller passes two equal strings.

## Verified work and practical limit

The feature branch contains:

```text
bedb7ad  Task 5 historical row assembler
7561ff0  Task 6 coverage accounting
4bd049e  Task 7 month partition writer
1dbdc23  Task 8 incremental selector
8725f35  Task 9 immutable generation writer
31b88a2  Task 10 provisional gate evaluator
67b1a98  Task 11 static feature/label firewall
```

Focused verification observed:

```text
Task 8 focused: 4 passed
Task 9 focused: 9 passed
Task 10 focused: 24 passed
Task 11 firewall and governance: 16 passed
Standalone verifier: PASS
```

The last complete full suite run after Task 10 was `886 passed, 1 skipped`.
Task 11's changed scan was separately tested as above; a new complete full
suite has not been run since this hard stop was found. No provider or data
network request was made in these tasks.

## Required next action

Keep the frozen Phase 1 and Phase 2A semantics. Before any pilot:

1. Implement the bridge design's real, bounded, exact-pinned five-domain
   artifact readers and month candidate/evidence-window producer. Prove
   source manifest, approval, revocation, composite, availability, and
   identity-chain integrity for every emitted candidate.
2. Replace self-asserted semantic gate equality with independently computed,
   artifact-bound predicate evidence. Add a regression where equal caller
   hashes cannot hide a wrong barrier/H5 schedule or wrong return.
3. Re-run a real source-pinned candidate census, then freeze the bounded pilot
   interval, complete candidate inventory, absent strata, five-domain pins,
   selection algorithm, and preregistration ID before observing pilot results.
4. Re-run Checkpoint 18 acceptance. Only a genuine PASS can open Checkpoint 19.

No pilot contract was frozen or pilot result observed in this checkpoint.
