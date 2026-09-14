# V5.2 Phase 2A Label Contract and Reference Engine Design

Status: `REVISED FOR CHATGPT REVIEW`

## 1. Scope and frozen base

Phase 2A defines future-outcome truth for one historical security identity and
one anchor trading session. It does not predict, rank, score, backtest, create
features, or bulk-materialize history.

The frozen base is commit
`892ff48f3fd77036e6c212d001bec5a7fe4cc538` and the accepted Phase 1C research
snapshot is
`9c5d3f3caddd359a79d7829dcdf87c254a3786fec639fe858d4a05a88168b1ee`.
Phase 0 through Phase 1C remain unchanged unless a Phase 2 failing test proves
a concrete correctness defect.

Phase 2A will later implement only:

```text
LabelContractV1
LabelInputBundleV1
LabelResultV1 / LabelValueV1
ReferenceLabelEngine
frozen acceptance inventory and independent reference ledger
```

It will not implement Phase 2B historical traversal or a label dataset.

Canonical Core V1 labels are:

```text
return_1d
return_3d
return_5d
max_favorable_excursion_5d
max_adverse_excursion_5d
hit_3pct_before_-2pct
hit_5pct_before_-3pct
```

## 2. Reused Phase 1 contracts

Phase 2A consumes, without redefining:

- `ResearchDataSnapshotV1` and its exact manifest IDs when a real snapshot
  exists for the relevant contemporaneous observation;
- approved trading-calendar sessions;
- Security Master identity and lifecycle lineage;
- Research Eligible Universe and `IPO_SEASONING_SESSIONS = 5`;
- `DailyBarFactV1` with `price_basis = UNADJUSTED_RAW`;
- approved Daily Security Status listing, suspension and identity facts;
- `CorporateActionFactV1`, its immutable revision lineage, scoped approval,
  coverage and quarantine rules;
- content hashing, manifest identity and fail-closed integrity conventions.

No provider client, raw response, mutable current-state pointer or unversioned
file is a valid label-engine input.

## 3. Approaches considered

### 3.1 Horizon semantics

1. **Strict exchange sessions (selected).** D+1, D+3 and D+5 are the first,
   third and fifth approved exchange-open sessions after D. This preserves one
   comparable clock for every security and exposes suspension as an outcome.
2. Security-tradable sessions. This produces a price at every endpoint, but a
   nominal 5d label can span five days for one security and months for another.
   It creates suspension-conditioned horizon bias and is rejected.
3. Publish both. This doubles the semantic surface before a research need has
   been demonstrated and is deferred.

### 3.2 Price comparability

1. **Raw bars plus approved corporate actions (selected).** An explicit
   self-financing wealth path provides reproducible economic comparability and
   fails closed on unsupported actions.
2. Provider forward-adjusted prices. Their adjustment vintage and revision
   lineage are not the approved source of truth and may incorporate future
   action knowledge; rejected.
3. Raw close return with action windows excluded. It is simple but discards
   valid cash-dividend and bonus-share cases that Phase 1 already supports;
   retained only as an independent cross-check for no-action samples.

### 3.3 Suspension endpoints

1. **Strict exchange horizon with proven suspension carry-forward (selected).**
   A full-day suspension has no trade and therefore no barrier hit. The last
   valid economic mark is carried through the suspended session, with approved
   corporate-action effects applied. This measures holding wealth, not
   executable liquidation value.
2. Mark every suspension window unsafe. Correct but unnecessarily loses cases
   whose absence of trading is authoritatively known.
3. Extend to the next trading day for the security. Rejected because it changes
   the horizon.

## 4. Causal boundary

```text
FEATURE SIDE
AnchorKnowledgeBoundary facts with available_at <= anchor_cutoff only

================ STRICT CAUSAL BOUNDARY ================

LABEL SIDE
LabelReferencePrice + later approved outcome facts
```

The boundary is machine-enforced as follows:

1. `v5_2.features` must not import `v5_2.labels` or label result types.
2. `LabelReferencePrice`, label-only future facts and their lineage live in
   `LabelInputBundleV1`; all three are forbidden from the feature namespace and
   feature tests/fixtures.
3. The reference engine receives values, not repositories or filesystem paths.
   It has no provider, network, raw-cache, current-pointer or environment access.
4. The input bundle always pins exact domain approvals, manifests and fact IDs.
   It pins anchor/outcome snapshot IDs only when those real snapshots exist.
   The engine rejects missing, tampered, revoked, mismatched or unpinned
   required-domain lineage.
5. A governance AST test rejects feature imports of labels and label imports of
   providers/integrations/raw acquisition. A sentinel test proves future values
   cannot appear in feature artifacts or shared fixtures.
6. Label `observed_at` and `LabelReferencePrice.available_at` are label-side
   metadata only. They must never be copied into an anchor knowledge fact.

The logical dependency is one-way: Phase 1 facts feed both future Feature work
and Labels; Labels never feed Features.

## 5. Anchor and session contract

Phase 2A freezes two separate anchor concepts:

```text
AnchorKnowledgeBoundary
    anchor_session = D
    anchor_cutoff = frozen D-close research cutoff
    eligible/PIT facts require available_at <= anchor_cutoff

LabelReferencePrice
    session = D
    price = approved unadjusted D close
    daily_bar_fact_id and manifest lineage are mandatory
    available_at may be later than anchor_cutoff
```

The AnchorKnowledgeBoundary governs Research Eligible Universe membership and
all future Feature-side inputs. The anchor security must be eligible at D under
the frozen five-session IPO seasoning rule, with resolved identity/status at the
anchor cutoff. Phase 2 does not recalculate eligibility.

The LabelReferencePrice is a prediction-target reference on the LABEL SIDE. For
historical reconstructed bars it may have `available_at > anchor_cutoff`,
including `NEXT_SESSION_SAFE @ next approved session 16:30`. This is valid label
reconstruction and is not evidence that D close was historically available to
feature computation. The invariant is explicit:

```text
D close used as label reference
!=
D close proven available to historical feature computation
```

The reference bar must still be approved, immutable, identity-correct and
unadjusted. Failure to keep it label-only is causal leakage.

Let `E(D, k)` be the kth approved exchange-open session strictly after D:

```text
H1 = E(D, 1)
H3 = E(D, 3)
H5 = E(D, 5)
window_5d = [E(D, 1), ..., E(D, 5)]
```

Natural dates and provider row order are forbidden. SSE and SZSE calendar
disagreement, missing calendar coverage or an uncompleted Hk makes the affected
label fail closed. If Hk has not yet completed in the pinned outcome lineage,
its state is `LABEL_PENDING`, not missing.

## 6. Label states and result granularity

Exactly three states are frozen for V1:

```text
LABEL_AVAILABLE
LABEL_PENDING
NOT_LABEL_SAFE
```

State is per label, not per anchor bundle. For example, `return_1d` may be
available while 5d labels are pending. `LabelValueV1` contains:

```text
label_name
state
value                 # Decimal or bool only when LABEL_AVAILABLE
reason_code            # required when not available; absent otherwise
horizon_end_session
observed_at            # completion/knowledge time of all inputs
input_fact_ids
contract_version
content_hash
```

`LABEL_PENDING` means the required exchange horizon has not completed.
`NOT_LABEL_SAFE` means it has completed but a correct value cannot be proven.
`CENSORED` is not introduced; terminal ambiguity maps to `NOT_LABEL_SAFE` with
a specific reason.

Minimum reason codes are:

```text
HORIZON_NOT_COMPLETED
ANCHOR_NOT_RESEARCH_ELIGIBLE
ANCHOR_BAR_MISSING
EXPECTED_BAR_MISSING
STATUS_UNRESOLVED
IDENTITY_UNRESOLVED
DELISTING_IN_HORIZON
UNSUPPORTED_CORPORATE_ACTION
CORPORATE_ACTION_COVERAGE_GAP
CORPORATE_ACTION_QUARANTINE
CORPORATE_ACTION_REVISION_INVALID
BARRIER_PATH_AMBIGUOUS
INPUT_LINEAGE_INVALID
```

Reasons are deterministic and precedence is frozen in the listed safety-check
order in section 12, so replay does not select different explanations.

## 7. Economic wealth path

All arithmetic uses Python `Decimal`; binary floating point is forbidden. No
intermediate value is rounded. Published numeric labels are quantized to
`0.00000001` with `ROUND_HALF_EVEN` and serialized as canonical decimal strings.

Start with one share immediately after the D close:

```text
P0 = close(D)
shares(D) = 1
cash(D) = 0
W(D, price) = P0
```

Before evaluating prices on each future session s, apply all approved effective
actions for s in deterministic `(effective_date, action_type, fact_id)` order.
For a cash dividend `c` per pre-action share and a bonus ratio `r` per
pre-action share:

```text
cash_s   = cash_prev + shares_prev * c
shares_s = shares_prev * (1 + r)
W_s(p)   = cash_s + shares_s * p
```

When cash and bonus actions share an effective date, cash is calculated from
pre-action shares, then bonus shares are added. Multiple actions compound in
the frozen ordering. Cancelled and superseded facts are excluded by the pinned
Corporate Action repository before the engine receives them.

Only `CASH_DIVIDEND` and `BONUS_SHARE` may be applied. A `RIGHTS_ISSUE`,
`STOCK_SPLIT` or `SHARE_CONVERSION` intersecting a label window makes that label
`NOT_LABEL_SAFE`. The same applies when supported-type coverage is absent,
quarantined or revision-invalid. Absence of returned events is treated as “no
event” only when the scoped approval and materialized coverage prove the exact
security-period query.

This is an economic holding-wealth return. It is not an executable liquidation
return and does not include tax, fees or slippage.

## 8. Bar and suspension semantics

For each required exchange session:

- a valid bar must satisfy the frozen OHLC/unit contract and match the resolved
  security identity;
- no bar plus approved full-day `SUSPENDED` status is a proven no-trade session;
- no bar plus `DELISTED` is handled by section 9;
- no bar before the horizon completes is pending only if the session itself is
  not complete;
- every other missing bar is `EXPECTED_BAR_MISSING` and `NOT_LABEL_SAFE`.

On a proven full-day suspension, the last valid close mark is carried forward.
Approved corporate actions effective that day still change shares/cash. There
is no open, high or low and therefore no barrier event. Max-upside/drawdown
checks include the carried economic close mark; they do not invent intraday
prices. When trading resumes, a valid resumption-session bar is mandatory.
Missing-bar inference is never used to manufacture a suspension fact.

This rule covers D+1 suspension, multi-session suspension, suspension across the
full five-session window and resumption before H5 without changing H1/H3/H5.

## 9. Delisting and identity transitions

An anchor at or after delisting is not research eligible. If an approved
delisting effective boundary intersects a label's horizon, V1 returns
`NOT_LABEL_SAFE/DELISTING_IN_HORIZON`. It does not infer a -100% return, a zero
return or a cash settlement from absent bars. A shorter horizon ending strictly
before the delisting boundary may remain available.

The engine uses a canonical economic security identity, not the displayed
symbol. A code or exchange identity transition may be crossed only when the
pinned Phase 1 identity graph provides one unambiguous predecessor-successor
chain and every bar/status/action fact resolves to it for its effective session.
The input bundle records both canonical identity and dated source identities.
Missing, conflicting or cyclic mapping returns
`NOT_LABEL_SAFE/IDENTITY_UNRESOLVED` for intersecting horizons.

## 10. Core label formulas

For a future session s, define economic values after applying actions effective
on or before s:

```text
R_close(s) = W_s(close_s) / P0 - 1
R_high(s)  = W_s(high_s)  / P0 - 1
R_low(s)   = W_s(low_s)   / P0 - 1
```

For a proven suspended session, all three path observations are replaced only
for return/max calculations by the carried close mark; the session contributes
no barrier hit.

### 10.1 Return labels

```text
return_1d = quantize(R_close(H1))
return_3d = quantize(R_close(H3))
return_5d = quantize(R_close(H5))
```

The numerator is economic wealth at the exact exchange-session endpoint. The
denominator is unadjusted D close for one initial share. There is no natural-day
counting and no next-tradable-session substitution.

### 10.2 Maximum favorable and adverse excursion

```text
max_favorable_excursion_5d = quantize(max(0, R_high(s) for s in window_5d))
max_adverse_excursion_5d   = quantize(min(0, R_low(s) for s in window_5d))
```

These labels use future daily high and low because they describe favorable and
adverse path excursion from the label reference price. The canonical research
fields are MFE/MAE and MAE is not classical peak-to-subsequent-trough drawdown.
`max_upside_5d` and `max_drawdown_5d` may exist only as UI/display aliases; they
must never appear as canonical stored label names. Limit-up/limit-down prices
are ordinary valid observations after the frozen bar checks. A supported
corporate action is handled by the wealth transform rather than mistaken for a
price jump.

### 10.3 Barrier labels

`BarrierOutcomeV1` is the minimal immutable calculation outcome:

```text
UPPER_FIRST
LOWER_FIRST
NEITHER
```

For `(u, l)` equal to `(0.03, -0.02)` and `(0.05, -0.03)`, inspect the five
future sessions in chronological order:

```text
upper_hit(s) = R_high(s) >= u
lower_hit(s) = R_low(s) <= l
```

- first decisive session upper only: `BarrierOutcomeV1.UPPER_FIRST`;
- first decisive session lower only: `BarrierOutcomeV1.LOWER_FIRST`;
- neither by H5: `BarrierOutcomeV1.NEITHER`;
- both on the first decisive session: `NOT_LABEL_SAFE` with
  `BARRIER_PATH_AMBIGUOUS` because daily OHLC cannot prove intraday order.

A prior-session decisive hit ends evaluation, so later ambiguity is irrelevant.
A gap can decide a barrier through valid open/high/low values. A proven suspended
session cannot hit either barrier. Limit prices require no special override.

Immutable calculation evidence retains `BarrierOutcomeV1` and the first
decisive session. The public boolean labels are derived without destroying that
information:

```text
UPPER_FIRST -> true
LOWER_FIRST -> false
NEITHER     -> false
```

### 10.4 Prediction target, not executable PnL

All Core V1 values describe future price movement or economic holding wealth
relative to the D-close LabelReferencePrice. They are prediction-target truth,
not after-close strategy executable realized return. A researcher operating
after D close cannot retroactively transact at that close.

Execution-aware evaluation of D+1 open, overnight gap, order tradability,
limit-state execution, fees and slippage belongs to later Research Evaluation /
Confirmation phases. None of those concerns changes the Phase 2A label formula.

## 11. Deferred label

`breakout_within_5d` is deferred to Phase 3. A meaningful breakout threshold
requires an anchor-time lookback definition such as a 20- or 60-session high.
Freezing it in Phase 2 would either duplicate a future Feature contract or create
a feature-label circular dependency. Phase 3 may define an anchor-known threshold
and pass that immutable value into a later label-contract version.

## 12. Reference engine input and evaluation order

`LabelInputBundleV1` contains only immutable, verified values:

```text
canonical_security_identity
anchor_session
AnchorKnowledgeBoundary value and evidence ID
LabelReferencePrice value and Daily Bar fact ID
anchor_snapshot_id        # optional; only when a real snapshot exists
outcome_snapshot_id       # optional; only when a real snapshot exists
provenance_path           # HISTORICAL or CONTEMPORANEOUS
Calendar approval/manifest/fact IDs
Security Master approval/manifest/identity fact IDs
Daily Bar approval/manifest/fact IDs
Security Status approval/manifest/fact IDs
Corporate Action approval/manifest/fact IDs
calendar_sessions D..H5
anchor eligibility evidence ID
dated identity-chain evidence IDs
future Security Status fact IDs/values
Corporate Action approval/manifest/fact IDs and exact coverage disposition
label_contract_version
bundle_hash
```

Two provenance paths are formally supported:

```text
HISTORICAL
approved immutable Phase 1B lineage
-> LabelInputBundleV1

CONTEMPORANEOUS / PRODUCTION
real ResearchDataSnapshot + its exact immutable domain lineage
-> LabelInputBundleV1
```

Historical materialization never manufactures synthetic daily
`ResearchDataSnapshot` artifacts. Snapshot IDs are optional provenance that are
pinned when real snapshots exist; exact required-domain lineage is mandatory in
both paths. Both paths converge on the same `LabelContractV1` and
`ReferenceLabelEngine`, and snapshot presence cannot change formulas or states.

Label availability is domain-minimal. Price/status/Corporate Action labels
require valid Calendar, Security Master/identity, Daily Bar, Security Status and
Corporate Action lineage for their exact interval. They do not require Financial
Disclosure readiness or any other unrelated domain. A contemporaneous snapshot
may contain six domains, but an unrelated scoped/not-ready domain cannot alter a
label whose actual dependencies remain valid.

Future facts and the LabelReferencePrice may have
`available_at > AnchorKnowledgeBoundary.anchor_cutoff`; that is expected on the
label side. Every output pins `observed_at = max(outcome session close,
available_at of every fact required for that label)`.

The small, pure `ReferenceLabelEngine` evaluates in this fixed order:

1. contract and bundle content integrity;
2. provenance-path validity, optional snapshot integrity, and mandatory exact
   required-domain lineage;
3. anchor Research Eligible Universe membership;
4. approved calendar and horizon completion;
5. identity chain;
6. listing/delisting boundary;
7. Corporate Action type, coverage, quarantine and revision safety;
8. status resolution and required-bar classification;
9. economic wealth path;
10. formulas and canonical result hashing.

It performs no I/O and makes no approval decision. A thin assembler outside the
engine may read pinned Phase 1 repositories and construct the input bundle; the
assembler must fail before engine invocation if an ID or hash does not verify.

Recommended minimal source layout for implementation is:

```text
src/v5_2/labels/contracts.py   # contract, input and result values
src/v5_2/labels/engine.py      # ordered safety evaluation and orchestration
src/v5_2/labels/calculation.py # wealth, returns, extrema and barriers
```

No additional platform, DAG, registry, task database or generic fact store is
introduced.

## 13. Frozen acceptance inventory design

Before any engine results are calculated, Phase 2A implementation must publish
one immutable `LabelAcceptanceInventoryV1` containing exact security identity,
anchor session, stratum, provenance path, optional real snapshot IDs, mandatory
domain-lineage IDs, expected source evidence types and selection-rule version.
Samples cannot be removed or replaced
after outcomes are observed. Inapplicable candidates are rejected during a
separate pre-result validity pass with recorded reasons.

The inventory has 18 mandatory, distinct real A-share anchor cases, one for each
stratum:

```text
01 normal positive return
02 normal negative return
03 high volatility
04 limit-up-like path
05 limit-down-like path
06 cash dividend
07 bonus share
08 D+1 full-day suspension
09 multi-day suspension
10 suspension through H5
11 resumption before H5
12 first IPO-eligible boundary
13 still inside IPO seasoning
14 delisting boundary
15 identity transition
16 expected future bar missing
17 unsupported corporate action
18 latest-session LABEL_PENDING
```

Barrier behavior is additionally frozen on real cases where available:

```text
19 upper barrier first
20 lower barrier first
21 neither barrier
22 same-session double-barrier ambiguity
```

Thus the target is 22 distinct real cases. If no independently provable real
case exists for a required exceptional stratum, the inventory preserves the
slot as `EVIDENCE_UNAVAILABLE`; a synthetic contract test may exercise the code
path but cannot make `REFERENCE SAMPLES` pass.

Selection is deterministic and preregistered: eligible candidates are ordered
by `content_hash(contract_version, stratum, canonical_identity, anchor_session)`
and the first candidate passing the pre-result validity checks is chosen. Across
the inventory, choose both exchanges, at least three calendar years, main/STAR/
ChiNext boards, and both positive and negative ordinary outcomes. No label result
may participate in candidate ordering except where the stratum itself necessarily
describes the independently established outcome.

## 14. Independent reference verification

Each frozen case receives a separate immutable
`IndependentLabelCalculationV1`, produced without importing or calling the
reference engine. It records:

```text
LabelReferencePrice and Daily Bar fact ID
H1/H3/H5 session derivation
every future OHLC input and fact ID
status interpretation
corporate-action arithmetic step by step
unrounded and rounded expected values
expected label state and reason
independent evidence IDs
calculator/method version
content hash
```

The verifier compares engine and independent records field by field: anchor,
horizons, price inputs, economic transformations, numeric/boolean result,
`BarrierOutcomeV1`, state, reason and lineage. A mismatch, unavailable required
real sample, or calculation
made by shared production code fails the gate. Synthetic unit tests supplement
but never replace this ledger.

## 15. Phase 2A acceptance gates

Phase 2A may declare completion only when fresh evidence reports:

```text
LABEL CONTRACT = FROZEN
CAUSAL ISOLATION = PASS
TRADING SESSION SEMANTICS = PASS
RETURN SEMANTICS = PASS
MFE/MAE SEMANTICS = PASS
BARRIER SEMANTICS = PASS
CORPORATE ACTION SAFETY = PASS
SUSPENSION SAFETY = PASS
DELISTING SAFETY = PASS
IDENTITY SAFETY = PASS
MISSING DATA FAIL-CLOSED = PASS
LABEL_PENDING = PASS
NOT_LABEL_SAFE = PASS
REFERENCE SAMPLES = PASS
INDEPENDENT VERIFICATION = PASS
DETERMINISTIC REPLAY = PASS
```

The acceptance suite must also include tampered/missing/revoked lineage,
unsupported actions, same-session barrier ambiguity, future horizon pending,
unexplained missing bar and feature-side leakage tests. Only all gates passing
permits:

```text
READY FOR PHASE 2B = YES
```

Phase 2A never publishes a historical Label Dataset or DatasetManifest.

## 16. Phase 2B interface, not implementation

Phase 2B will consume the frozen `LabelContractV1`, the accepted reference engine
and eligible anchor inventory traversal. It is responsible for:

```text
historical security x anchor-session traversal
bulk deterministic calculation
per-label AVAILABLE/PENDING/NOT_SAFE coverage accounting
reason-coded exclusions and systematic-defect audit
immutable partitioned label facts
Label DatasetManifest pinned to exact input domain lineage, optional real
snapshot provenance, and contract version
deterministic rematerialization and broad historical acceptance
```

The Phase 2A engine API remains scalar/auditable. Phase 2B may batch around it
but must not change formulas, state precedence or safety policy. Any optimized
implementation must match the reference engine over the full frozen acceptance
inventory and additional preregistered samples.

## 17. Open design questions

There are no blocking semantic questions for implementing Core V1 after this
document is approved. Two explicitly deferred product choices remain:

1. whether future research needs a second, security-tradable-session horizon;
2. the anchor-known resistance definition for `breakout_within_5d` in Phase 3.

Neither changes the Core V1 contract or authorizes implementation in this turn.
