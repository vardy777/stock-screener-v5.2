# V5.2 Phase 2A Label Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and independently validate the scalar, deterministic Phase 2A Core V1 label contract and reference engine without bulk historical materialization.

**Architecture:** Immutable label-only input values pin the exact Phase 1 domain lineage needed by each label. Pure calculation functions implement exchange-session horizons, an unadjusted-bar plus approved-corporate-action wealth path, MFE/MAE and barrier outcomes; a small engine applies the frozen fail-closed evaluation order. Real-sample inventory, independent arithmetic and acceptance evaluation remain outside the engine and produce content-addressed evidence.

**Tech Stack:** Python 3.12, standard-library `dataclasses`, `enum.StrEnum`, `datetime`, `decimal.Decimal`, existing `v5_2.data.identity` canonical hashing, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-v5-2-phase-2a-label-engine-design.md`

## Global Constraints

- Frozen semantic base: design commit `6f10fd3c7b3d0ff5cf3ae2bc1d644fe0fe427d42`; Phase 1C base `892ff48f3fd77036e6c212d001bec5a7fe4cc538`.
- Core canonical labels are `return_1d`, `return_3d`, `return_5d`, `max_favorable_excursion_5d`, `max_adverse_excursion_5d`, `hit_3pct_before_-2pct`, and `hit_5pct_before_-3pct`.
- `breakout_within_5d`, Feature, Ranking, ML, Backtest and all Phase 2B bulk materialization are excluded.
- Historical provenance pins exact immutable Phase 1B domain lineage without synthetic daily snapshots. Contemporaneous provenance pins a real snapshot plus the same exact domain lineage.
- Required domains are Calendar, Security Master/identity, Daily Bar, Daily Security Status and Corporate Action. Financial Disclosure is not a dependency.
- `AnchorKnowledgeBoundary` and `LabelReferencePrice` are distinct. Historical D close may be `NEXT_SESSION_SAFE` and later than the anchor cutoff; it remains label-only.
- The reference engine has no filesystem, provider, network, raw-cache, current-pointer or environment dependency.
- All numeric label arithmetic uses `Decimal`, no intermediate rounding, then `quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)`.
- Every task uses RED -> minimal GREEN -> focused regression. Do not modify Phase 0-1C unless a failing test proves a concrete correctness defect.
- Implementation execution starts from a clean isolated worktree created by `superpowers:using-git-worktrees`; this plan-writing turn creates no worktree.

## Planned file map

Create:

```text
src/v5_2/labels/contracts.py
src/v5_2/labels/calculation.py
src/v5_2/labels/engine.py
src/v5_2/labels/acceptance.py
scripts/freeze_phase2a_samples.py
scripts/verify_phase2a_reference.py
scripts/accept_phase2a.py
tests/labels/test_contracts.py
tests/labels/test_horizons.py
tests/labels/test_wealth_path.py
tests/labels/test_safety.py
tests/labels/test_outcome_labels.py
tests/labels/test_barriers.py
tests/labels/test_reference_engine.py
tests/labels/test_causal_isolation.py
tests/labels/test_real_acceptance_inventory.py
tests/labels/test_independent_reference.py
tests/labels/test_phase2a_acceptance.py
docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md
```

Modify only where stated:

```text
src/v5_2/labels/__init__.py
tests/governance/test_phase_1a_boundaries.py
README.md
```

Repository-local immutable evidence is written under ignored
`data/phase_2a/{governance,reference}/`; it is not a new generic fact store and
is never packaged into the wheel.

---

### Task 1: Immutable label contracts

**Files:**
- Create: `src/v5_2/labels/contracts.py`
- Modify: `src/v5_2/labels/__init__.py`
- Create: `tests/labels/test_contracts.py`

**Interfaces:**
- Consumes: `v5_2.data.identity.canonical_json`, `content_hash`; existing `DailyBarFactV1`, `DailySecurityStatusFactV1`, and `CorporateActionFactV1` only as typed immutable inputs.
- Produces: `LabelState`, `LabelReasonCode`, `BarrierOutcomeV1`, `ProvenancePath`, `AnchorKnowledgeBoundary`, `LabelReferencePrice`, `LabelContractV1`, `LabelValueV1`, `LabelResultV1`, and `LabelInputBundleV1`.

- [ ] **Step 1: Write the contract-state RED tests**

Add tests named:

```text
test_available_value_requires_value_and_forbids_reason — construct AVAILABLE with Decimal and reject a reason
test_pending_value_requires_horizon_reason_and_no_value — accept HORIZON_NOT_COMPLETED only with value=None
test_not_safe_value_requires_reason_and_no_value — accept safety reason only with value=None
test_numeric_value_must_be_decimal_not_float — reject float construction
test_boolean_value_is_allowed_only_for_barrier_label — reject bool for return/MFE/MAE
test_canonical_label_names_exclude_ui_excursion_aliases — reject max_upside/max_drawdown
test_contract_and_result_hashes_replay_identically — equal semantic input gives byte-identical identity
test_tampered_contract_or_result_hash_is_rejected — changed field fails verify()
```

Construct one available return, one pending 5d label and one unsafe barrier.
Assert `max_upside_5d` and `max_drawdown_5d` are rejected as canonical names.

- [ ] **Step 2: Run the state tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_contracts.py -q
```

Expected: collection fails because `v5_2.labels.contracts` does not exist.

- [ ] **Step 3: Implement enums, anchor types and value/result contracts**

Use frozen dataclasses and these public enum values:

```python
class LabelState(StrEnum):
    LABEL_AVAILABLE = "LABEL_AVAILABLE"
    LABEL_PENDING = "LABEL_PENDING"
    NOT_LABEL_SAFE = "NOT_LABEL_SAFE"

class BarrierOutcomeV1(StrEnum):
    UPPER_FIRST = "UPPER_FIRST"
    LOWER_FIRST = "LOWER_FIRST"
    NEITHER = "NEITHER"

class ProvenancePath(StrEnum):
    HISTORICAL = "HISTORICAL"
    CONTEMPORANEOUS = "CONTEMPORANEOUS"
```

Define every reason from design section 6. `AnchorKnowledgeBoundary` pins D,
timezone-aware cutoff, eligibility evidence ID and `research_eligible`.
`LabelReferencePrice` pins D, positive `Decimal` price, `UNADJUSTED_RAW`, exact
Daily Bar fact ID and timezone-aware `available_at`. Give each type `create`,
`verify`, `as_dict`, and content identity through `content_hash`.

- [ ] **Step 4: Write provenance/input RED tests**

Add:

```text
test_historical_bundle_is_valid_without_snapshot_ids — HISTORICAL accepts both snapshot IDs as None
test_contemporaneous_bundle_requires_real_anchor_and_outcome_snapshot_ids — missing either 64-hex ID raises contract error
test_invalid_provenance_value_is_rejected — unknown enum input raises ValueError
test_bundle_requires_exact_five_domain_lineage_and_not_financial — omission/addition fails validation
test_optional_snapshot_ids_are_content_hashed_when_present — changing a real snapshot ID changes bundle hash
test_reference_price_may_be_available_after_anchor_cutoff — NEXT_SESSION_SAFE historical price is accepted
test_reference_price_session_must_equal_anchor_session — differing sessions raise contract error
test_bundle_rejects_tampered_hash_and_mismatched_identity — verify() is false for either mutation
```

Use mandatory lineage keys exactly:

```python
REQUIRED_LABEL_DOMAINS = (
    "trade_calendar", "security_master", "daily_bar",
    "daily_security_status", "corporate_action",
)
```

Each domain value is a non-empty tuple of exact 64-character lowercase hex
approval/manifest/fact IDs. Reject `financial_disclosure` as a required-domain
key rather than silently adding it.

- [ ] **Step 5: Implement `LabelContractV1` and `LabelInputBundleV1` minimally**

Freeze contract version `v5.2-label-contract-v1`, horizons `(1, 3, 5)`, five-day
window, quantization `0.00000001`, rounding `ROUND_HALF_EVEN`, supported CA types
and the two barrier pairs. The bundle includes exact domain lineage, optional
snapshot IDs, anchor boundary/reference, approved exchange sessions, future
bars/statuses/actions, CA coverage/quarantine/revision dispositions and a hash.
Do not add any repository loader.

- [ ] **Step 6: Run contract tests GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_contracts.py -q
```

Expected: all contract tests pass.

- [ ] **Step 7: Commit checkpoint**

```powershell
git add src/v5_2/labels/__init__.py src/v5_2/labels/contracts.py tests/labels/test_contracts.py
git commit -m "feat: add Phase 2A label contracts"
```

### Task 2: Pure exchange-session horizons

**Files:**
- Create: `src/v5_2/labels/calculation.py`
- Create: `tests/labels/test_horizons.py`

**Interfaces:**
- Consumes: `anchor_session: date`, `approved_exchange_sessions: tuple[date, ...]`, `latest_completed_session: date`.
- Produces: `LabelHorizonsV1` and `resolve_label_horizons(anchor_session: date, approved_exchange_sessions: tuple[date, ...], latest_completed_session: date) -> LabelHorizonsV1`; raises `IncompleteCalendarCoverage` only for structurally unprovable calendars and reports per-horizon pending through the returned value.

- [ ] **Step 1: Write horizon RED tests**

Add:

```text
test_horizons_skip_weekend_without_counting_natural_days — Friday D yields Monday H1
test_horizons_skip_holiday_and_multiday_market_closure — only supplied open sessions count
test_horizons_cross_year_boundary — December D resolves January sessions in order
test_horizon_uses_exchange_sessions_even_when_security_is_suspended — status never changes H values
test_incomplete_future_sessions_are_pending_not_missing — known H after latest_completed is pending
test_missing_calendar_coverage_fails_closed — fewer than five known future opens raises coverage error
test_duplicate_or_unsorted_calendar_is_canonicalized_deterministically — output is sorted and unique
```

Use explicit dates and assert H1/H3/H5 plus the exact five-session window.

- [ ] **Step 2: Run the horizon tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_horizons.py -q
```

Expected: import failure for `resolve_label_horizons`.

- [ ] **Step 3: Implement the pure resolver**

Implement:

```python
def resolve_label_horizons(
    anchor_session: date,
    approved_exchange_sessions: tuple[date, ...],
    latest_completed_session: date,
) -> LabelHorizonsV1:
    future = tuple(day for day in sorted(set(approved_exchange_sessions)) if day > anchor_session)
    # preserve known H values; mark an H pending when it is after latest_completed_session
```

Require that D is present and that calendar lineage supplies at least five
future approved sessions; otherwise fail closed as calendar coverage, not as a
security suspension. Never inspect per-security status here.

- [ ] **Step 4: Run horizon tests GREEN and contract regression**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_horizons.py tests/labels/test_contracts.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels/calculation.py tests/labels/test_horizons.py
git commit -m "feat: add exchange-session label horizons"
```

### Task 3: Economic holding-wealth path

**Files:**
- Modify: `src/v5_2/labels/calculation.py`
- Create: `tests/labels/test_wealth_path.py`

**Interfaces:**
- Consumes: `LabelReferencePrice`, ordered sessions, verified unadjusted bars, approved `CorporateActionFactV1` values, and explicit CA coverage/quarantine/revision dispositions.
- Produces: `EconomicPathPointV1`, `EconomicWealthPathV1`, and `build_economic_wealth_path(reference_price: LabelReferencePrice, sessions: tuple[date, ...], bars: tuple[DailyBarFactV1, ...], actions: tuple[CorporateActionFactV1, ...], action_coverage: CorporateActionCoverageV1) -> EconomicWealthPathV1`; raises a reason-bearing `UnsafeLabelInput` consumed by Task 7.

- [ ] **Step 1: Write wealth-path RED tests**

Add:

```text
test_no_action_wealth_equals_one_share_times_raw_price — shares=1, cash=0 for every point
test_cash_dividend_adds_cash_using_pre_action_shares — W=shares*price+shares_pre*c
test_bonus_share_multiplies_shares_before_session_prices — shares=shares_pre*(1+r)
test_same_day_cash_then_bonus_uses_frozen_order — cash uses pre-bonus shares
test_multiple_supported_actions_compound_by_date_type_and_fact_id — exact ordered step ledger matches
test_unsupported_rights_split_or_conversion_is_not_safe — each type returns UNSUPPORTED_CORPORATE_ACTION
test_coverage_gap_is_not_safe_not_no_event — returns CORPORATE_ACTION_COVERAGE_GAP
test_quarantined_security_period_is_not_safe — returns CORPORATE_ACTION_QUARANTINE
test_invalid_revision_lineage_is_not_safe — returns CORPORATE_ACTION_REVISION_INVALID
test_adjusted_provider_bar_is_rejected — any basis other than UNADJUSTED_RAW fails
test_path_uses_decimal_and_does_not_round_intermediate_wealth — repeating decimal survives until output
```

Manually assert shares, cash, high/low/close wealth at every action date.

- [ ] **Step 2: Run wealth tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_wealth_path.py -q
```

- [ ] **Step 3: Implement the minimal wealth path**

Apply supported actions before the session price in ordering
`(effective_date, action_type, fact_id)`. For a session's same-day cash `c` and
bonus ratio `r`, calculate `cash += pre_shares*c`, then
`shares = pre_shares*(1+r)`. Reject unsupported action types before calculating
any value. Keep unrounded `Decimal` points and all consumed fact IDs.

- [ ] **Step 4: Run wealth/horizon tests GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_wealth_path.py tests/labels/test_horizons.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels/calculation.py tests/labels/test_wealth_path.py
git commit -m "feat: add label economic wealth path"
```

### Task 4: Bar, suspension, identity and delisting safety

**Files:**
- Create: `src/v5_2/labels/engine.py`
- Create: `tests/labels/test_safety.py`

**Interfaces:**
- Consumes: `LabelInputBundleV1`, `LabelHorizonsV1` and exact dated Phase 1 facts.
- Produces: `ValidatedLabelWindowV1` and `validate_label_window(bundle, horizons) -> ValidatedLabelWindowV1 | UnsafeWindowV1`.

- [ ] **Step 1: Write safety RED tests**

Add:

```text
test_normal_bar_window_is_safe — five valid bars produce five tradable points
test_full_day_suspension_carries_last_close_and_has_no_intraday_range — mark carries and intraday_trade=False
test_multiday_and_full_horizon_suspensions_do_not_extend_exchange_horizon — H1/H3/H5 remain unchanged
test_resumption_requires_valid_bar — resumed status without bar is EXPECTED_BAR_MISSING
test_unexplained_missing_bar_is_expected_bar_missing — no status inference is allowed
test_missing_bar_is_never_inferred_as_suspension_zero_or_delisting — all three fabricated meanings are absent
test_verified_identity_transition_maps_dated_source_identity — predecessor/successor resolve to one canonical ID
test_ambiguous_cyclic_or_missing_identity_chain_is_not_safe — each yields IDENTITY_UNRESOLVED
test_delisting_inside_each_affected_horizon_is_not_safe — only intersecting horizons fail
test_delisting_never_implies_minus_one_return — unsafe result has value=None
```

Assert exact `LabelReasonCode` and affected horizon. A shorter horizon strictly
before delisting remains safe.

- [ ] **Step 2: Run safety tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_safety.py -q
```

- [ ] **Step 3: Implement ordered safety validation**

Validate identity and listing boundaries before classifying bars. A missing bar
is carry-forward only when the pinned status fact explicitly proves full-day
`SUSPENDED`. Represent suspension path points with prior close wealth and
`intraday_trade=False`. On resumption require a valid raw bar. Return unsafe
reason values; do not create `LabelValueV1` yet.

- [ ] **Step 4: Run safety and prior focused tests GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_safety.py tests/labels/test_wealth_path.py tests/labels/test_horizons.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels/engine.py tests/labels/test_safety.py
git commit -m "feat: enforce label window safety"
```

### Task 5: Return, MFE and MAE calculations

**Files:**
- Modify: `src/v5_2/labels/calculation.py`
- Create: `tests/labels/test_outcome_labels.py`

**Interfaces:**
- Consumes: `EconomicWealthPathV1`, H1/H3/H5.
- Produces: `calculate_return(path, horizon) -> Decimal`, `calculate_mfe_5d(path) -> Decimal`, and `calculate_mae_5d(path) -> Decimal`.

- [ ] **Step 1: Write numeric-label RED tests**

Add:

```text
test_return_1d_3d_5d_positive_negative_and_zero — exact endpoint Decimal ratios match
test_suspension_endpoint_uses_carried_economic_close — return uses the carried wealth
test_cash_and_bonus_windows_use_economic_wealth — a fixture whose ex-price change exactly offsets the approved distribution has zero economic return
test_mfe_uses_future_economic_high_relative_to_reference — maximum high ratio is selected
test_mae_uses_future_economic_low_relative_to_reference — minimum low ratio is selected
test_mfe_and_mae_include_zero_floor_and_ceiling — MFE>=0 and MAE<=0
test_quantization_is_eight_places_round_half_even — tie cases round to even
test_intermediate_path_values_are_not_rounded — only final labels are quantized
test_canonical_results_never_emit_max_upside_or_max_drawdown — exact seven-name set excludes aliases
```

- [ ] **Step 2: Run numeric tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_outcome_labels.py -q
```

- [ ] **Step 3: Implement formulas exactly**

Use:

```python
return_h = quantize(path[h].close_wealth / path.reference_price - Decimal("1"))
mfe = quantize(max(Decimal("0"), *(p.high_wealth / p0 - 1 for p in window)))
mae = quantize(min(Decimal("0"), *(p.low_wealth / p0 - 1 for p in window)))
```

For suspension points use the carried close wealth for return/MFE/MAE; do not
manufacture an intraday high or low. Keep canonical names only.

- [ ] **Step 4: Run calculation suite GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_outcome_labels.py tests/labels/test_wealth_path.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels/calculation.py tests/labels/test_outcome_labels.py
git commit -m "feat: calculate return MFE and MAE labels"
```

### Task 6: Barrier outcome calculation

**Files:**
- Modify: `src/v5_2/labels/calculation.py`
- Create: `tests/labels/test_barriers.py`

**Interfaces:**
- Consumes: `EconomicWealthPathV1`, upper/lower `Decimal` thresholds.
- Produces: `BarrierCalculationV1(outcome, first_decisive_session, boolean_value)` or `UnsafeLabelInput(BARRIER_PATH_AMBIGUOUS)` through `calculate_barrier(path: EconomicWealthPathV1, upper_return: Decimal, lower_return: Decimal) -> BarrierCalculationV1`.

- [ ] **Step 1: Write barrier RED tests**

Add:

```text
test_upper_first_retains_outcome_and_derives_true — outcome UPPER_FIRST, boolean true
test_lower_first_retains_outcome_and_derives_false — outcome LOWER_FIRST, boolean false
test_neither_retains_outcome_and_derives_false — outcome NEITHER, boolean false
test_same_first_decisive_session_both_is_not_safe — exact ambiguity reason and no value
test_prior_decisive_session_ignores_later_double_hit — earlier outcome remains final
test_gap_uses_valid_daily_range_without_intraday_guess — single-sided gap resolves that session
test_limit_up_like_and_limit_down_like_paths — valid limit ranges resolve normally
test_suspended_session_cannot_hit_barrier — intraday_trade=False is skipped
test_corporate_action_transforms_economic_barrier_prices — wealth ratios, not raw price ratios, decide
```

- [ ] **Step 2: Run barrier tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_barriers.py -q
```

- [ ] **Step 3: Implement first-decisive-session iteration**

Skip `intraday_trade=False` points. For each remaining session calculate upper
from economic high and lower from economic low. Return the three-valued outcome
and first decisive session. If both are true at the first decisive session,
raise the exact ambiguous reason. Derive boolean only at result construction.

- [ ] **Step 4: Run barrier/calculation tests GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_barriers.py tests/labels/test_outcome_labels.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels/calculation.py tests/labels/test_barriers.py
git commit -m "feat: preserve label barrier outcomes"
```

### Task 7: Pure `ReferenceLabelEngine`

**Files:**
- Modify: `src/v5_2/labels/engine.py`
- Modify: `src/v5_2/labels/__init__.py`
- Create: `tests/labels/test_reference_engine.py`

**Interfaces:**
- Consumes: `LabelInputBundleV1` only.
- Produces: `ReferenceLabelEngine.evaluate(bundle: LabelInputBundleV1) -> LabelResultV1` with seven per-label values and immutable barrier calculation evidence.

- [ ] **Step 1: Write engine-order and result RED tests**

Add:

```text
test_historical_and_contemporaneous_provenance_produce_same_result — equal domain facts yield equal values
test_snapshot_presence_never_changes_formula_or_state — adding valid snapshot IDs changes provenance hash only
test_engine_returns_seven_canonical_core_labels — exact frozen name set is returned
test_one_day_available_while_five_day_labels_pending — per-label states differ safely
test_not_safe_is_scoped_to_intersecting_horizons — shorter pre-defect label remains available
test_failure_reason_precedence_matches_frozen_order — first failing gate supplies the reason
test_tampered_missing_or_revoked_required_lineage_fails_first — INPUT_LINEAGE_INVALID wins
test_financial_readiness_is_absent_and_cannot_gate_labels — no financial input exists
test_same_bundle_replays_to_same_result_hash — result serialization is byte-identical
test_engine_object_has_no_path_client_repository_or_environment_input — signature accepts bundle only
```

- [ ] **Step 2: Run engine tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_reference_engine.py -q
```

- [ ] **Step 3: Implement the scalar engine in frozen order**

Implement integrity/provenance, eligibility, calendar, identity, delisting, CA,
status/bar, wealth and formula evaluation in the exact spec order. Construct
per-label pending/unsafe results so a longer horizon cannot invalidate a safe
shorter one. Set `observed_at` to the maximum required input availability and
completed-session close. Do not perform I/O or approval resolution.

- [ ] **Step 4: Run all Phase 2A pure tests GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_contracts.py tests/labels/test_horizons.py tests/labels/test_wealth_path.py tests/labels/test_safety.py tests/labels/test_outcome_labels.py tests/labels/test_barriers.py tests/labels/test_reference_engine.py -q
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add src/v5_2/labels tests/labels
git commit -m "feat: add deterministic reference label engine"
```

### Task 8: Causal-isolation governance

**Files:**
- Modify: `tests/governance/test_phase_1a_boundaries.py`
- Create: `tests/labels/test_causal_isolation.py`

**Interfaces:**
- Consumes: repository AST and source-file inventory.
- Produces: machine-enforced import/type/fixture boundary; no runtime API.

- [ ] **Step 1: Write governance RED tests**

Add tests:

```text
test_features_cannot_import_labels_or_label_only_types — AST findings are empty
test_feature_sources_and_fixtures_cannot_name_label_input_bundle — token scan findings are empty
test_feature_sources_cannot_name_label_reference_price — token scan findings are empty
test_label_engine_cannot_import_providers_integrations_or_acquisition — forbidden import findings are empty
test_label_engine_has_no_filesystem_network_environment_or_current_pointer_access — forbidden API findings are empty
test_future_fact_sentinel_is_detected_in_feature_artifact — planted temp artifact yields one exact finding
test_current_feature_namespace_contains_no_future_fact_sentinel — repository findings are empty
```

Parse imports with `ast`; scan only active source/tests and exclude immutable
label acceptance artifacts from the feature scan.

- [ ] **Step 2: Run governance tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_causal_isolation.py tests/governance/test_phase_1a_boundaries.py -q
```

- [ ] **Step 3: Add the minimal governance seam**

Extend the existing boundary helpers/test inventory rather than adding a new
governance framework. If current code already passes an assertion, retain the
test as the seam; make production changes only for proven violations.

- [ ] **Step 4: Run governance and standalone checks GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_causal_isolation.py tests/governance/test_phase_1a_boundaries.py -q
.\.venv\Scripts\python.exe scripts\verify_standalone.py
```

- [ ] **Step 5: Commit checkpoint**

```powershell
git add tests/labels/test_causal_isolation.py tests/governance/test_phase_1a_boundaries.py
git commit -m "test: enforce label causal isolation"
```

### Task 9: Freeze the real 22-case acceptance inventory

**Files:**
- Create: `src/v5_2/labels/acceptance.py`
- Create: `scripts/freeze_phase2a_samples.py`
- Create: `tests/labels/test_real_acceptance_inventory.py`
- Write immutable runtime artifacts: `data/phase_2a/governance/label-acceptance-selection-rule-<hash>.json`, `label-acceptance-inventory-<hash>.json`

**Interfaces:**
- Consumes: approved Phase 1B facts, exact lineage IDs and frozen selection rule; never consumes `ReferenceLabelEngine` results.
- Produces: `LabelAcceptanceSelectionRuleV1`, 22 `LabelAcceptanceSlotV1` values and `LabelAcceptanceInventoryV1`.

- [ ] **Step 1: Write inventory-contract RED tests**

Add:

```text
test_inventory_has_exactly_22_named_distinct_slots — exact slot names/count and distinct anchors
test_inventory_requires_exact_lineage_or_evidence_unavailable — every slot satisfies one branch
test_historical_slots_do_not_require_snapshot_ids — valid historical slot has None snapshots
test_real_snapshot_ids_are_pinned_when_present — contemporaneous slot carries exact IDs
test_selection_order_is_content_hash_not_engine_outcome — candidate order matches canonical hashes
test_inapplicable_candidate_is_recorded_before_result_calculation — exclusion record predates result ledger
test_inventory_covers_exchanges_years_and_boards — both exchanges, three years, main/STAR/ChiNext
test_frozen_inventory_rejects_mutation_or_replacement — changed slot breaks inventory hash
```

- [ ] **Step 2: Run inventory tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_real_acceptance_inventory.py -q
```

- [ ] **Step 3: Implement inventory contracts and pre-result selector**

Put immutable inventory dataclasses and verification in `acceptance.py`. The
script loads only approved Phase 1 artifacts, performs pre-result applicability
checks, orders candidates by
`content_hash(contract_version, stratum, canonical_identity, anchor_session)`,
and freezes the first valid candidate. It must not import `ReferenceLabelEngine`
or `v5_2.labels.calculation`. Preserve any unavailable slot as
`EVIDENCE_UNAVAILABLE`; never replace it with synthetic evidence.

- [ ] **Step 4: Run the selector once and inspect the frozen inventory**

```powershell
.\.venv\Scripts\python.exe scripts\freeze_phase2a_samples.py
.\.venv\Scripts\python.exe -m pytest tests/labels/test_real_acceptance_inventory.py -q
```

Expected: immutable selection-rule and inventory IDs print; all 22 slots remain
present; the script exits nonzero only for structural/tamper defects, not because
an exceptional slot honestly has `EVIDENCE_UNAVAILABLE`.

- [ ] **Step 5: Commit contracts/script/tests but not ignored data**

```powershell
git add src/v5_2/labels/acceptance.py scripts/freeze_phase2a_samples.py tests/labels/test_real_acceptance_inventory.py
git commit -m "feat: freeze Phase 2A real sample inventory"
```

### Task 10: Independent reference ledger and comparison

**Files:**
- Create: `scripts/verify_phase2a_reference.py`
- Create: `tests/labels/test_independent_reference.py`
- Write immutable runtime artifacts: `data/phase_2a/reference/independent-label-calculation-<hash>.json`, `engine-comparison-<hash>.json`

**Interfaces:**
- Consumes: frozen inventory, exact Phase 1 facts and engine results.
- Produces: `IndependentLabelCalculationV1` records and field-by-field comparison evidence. The independent calculator must not import production `engine.py` or `calculation.py`.

- [ ] **Step 1: Write independence and ledger RED tests**

Add:

```text
test_independent_script_does_not_import_engine_or_calculation — AST forbidden imports are empty
test_ledger_records_reference_horizons_ohlc_status_ca_steps_and_lineage — all required fields are nonempty
test_ledger_records_unrounded_and_round_half_even_values — both forms match hand arithmetic
test_ledger_retains_barrier_outcome_and_first_decisive_session — neither field is collapsed
test_comparison_detects_value_state_reason_or_lineage_mismatch — each single mutation fails
test_synthetic_case_cannot_satisfy_real_reference_slot — source_kind SYNTHETIC is rejected
test_identical_reference_run_has_identical_content_hash — canonical bytes and ID match
```

- [ ] **Step 2: Run independent-reference tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_independent_reference.py -q
```

- [ ] **Step 3: Implement independent arithmetic in the script**

Use only standard-library Decimal plus Phase 1 fact deserialization and contract
enums. Recompute H1/H3/H5, shares/cash, economic OHLC, returns, MFE/MAE and
barriers in visibly separate functions. Do not call or copy callable production
helpers. Persist every required input, intermediate and expected output with a
method version and content hash.

- [ ] **Step 4: Compare engine and independent results**

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase2a_reference.py
.\.venv\Scripts\python.exe -m pytest tests/labels/test_independent_reference.py -q
```

Expected: every evidence-available frozen real slot matches field by field.
Any required `EVIDENCE_UNAVAILABLE` slot keeps `REFERENCE SAMPLES` pending; the
script must not lower the gate or silently omit it.

- [ ] **Step 5: Commit checkpoint**

```powershell
git add scripts/verify_phase2a_reference.py tests/labels/test_independent_reference.py
git commit -m "test: independently verify Phase 2A labels"
```

### Task 11: Phase 2A acceptance artifact and exit verification

**Files:**
- Modify: `src/v5_2/labels/acceptance.py`
- Create: `scripts/accept_phase2a.py`
- Create: `tests/labels/test_phase2a_acceptance.py`
- Create: `docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md`
- Modify: `README.md`
- Write immutable runtime artifact: `data/phase_2a/governance/phase2a-acceptance-<hash>.json`

**Interfaces:**
- Consumes: frozen contract, all focused test/gate evidence, frozen inventory and independent comparisons.
- Produces: `Phase2AAcceptanceArtifactV1`, report, and `ready_for_phase_2b` only when all 16 gates pass.

- [ ] **Step 1: Write acceptance RED tests**

Add:

```text
test_acceptance_requires_exact_16_frozen_gates — missing, extra or renamed gate is rejected
test_any_failed_pending_missing_or_tampered_gate_blocks_phase2b — ready flag remains false
test_unavailable_real_reference_slot_blocks_reference_samples_gate — gate remains non-PASS
test_all_pass_produces_ready_for_phase2b_yes — exact 16 PASS values set true
test_acceptance_hash_replays_deterministically — same evidence gives same ID/bytes
test_acceptance_does_not_create_label_dataset_or_manifest — no matching output path exists
```

- [ ] **Step 2: Run acceptance tests RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_phase2a_acceptance.py -q
```

- [ ] **Step 3: Implement the exact acceptance evaluator**

Require these names and no substitutes:

```text
LABEL CONTRACT
CAUSAL ISOLATION
TRADING SESSION SEMANTICS
RETURN SEMANTICS
MFE/MAE SEMANTICS
BARRIER SEMANTICS
CORPORATE ACTION SAFETY
SUSPENSION SAFETY
DELISTING SAFETY
IDENTITY SAFETY
MISSING DATA FAIL-CLOSED
LABEL_PENDING
NOT_LABEL_SAFE
REFERENCE SAMPLES
INDEPENDENT VERIFICATION
DETERMINISTIC REPLAY
```

The CLI reads immutable evidence, verifies IDs/hashes and emits the artifact and
human report. It must keep `READY FOR PHASE 2B = NO` for any non-PASS gate.

- [ ] **Step 4: Run focused Phase 2A tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels -q
```

Record the exact count and duration in the report.

- [ ] **Step 5: Run Phase 0-1C and full regression**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/data tests/real_audits tests/refresh tests/governance -q
.\.venv\Scripts\python.exe -m pytest -q
```

Any regression blocks acceptance; do not loosen earlier gates.

- [ ] **Step 6: Run standalone, clean-room, build/wheel and zero-dependency acceptance**

```powershell
.\.venv\Scripts\python.exe scripts\verify_standalone.py
.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
```

The clean-room JSON must report build, install, tests, wheel smoke and
`zero_dependency_acceptance=true` with empty archive findings.

- [ ] **Step 7: Run credential and AST causal-isolation scans**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/labels/test_causal_isolation.py tests/governance/test_phase_1a_boundaries.py -q
```

Use the existing actual-secret sentinel procedure across tracked/candidate files
and `data/phase_2a`, excluding the ignored `.env`; print counts only. Require
zero findings, `.env` ignored and `.env` untracked.

- [ ] **Step 8: Prove deterministic replay**

Hash every `data/phase_2a` file, rerun
`freeze_phase2a_samples.py`, `verify_phase2a_reference.py`, and
`accept_phase2a.py`, then compare paths and SHA-256 values. Require identical
artifact IDs, file count and bytes; no duplicate artifact or mutable overwrite.

- [ ] **Step 9: Complete report and diff hygiene**

Update `docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md` with exact commands, test
counts, inventory/ledger/acceptance IDs, all gate results and remaining blockers.
Add only the scalar Phase 2A usage/boundary to README. Run:

```powershell
git diff --check
git status --short
```

- [ ] **Step 10: Commit, push, verify and STOP**

Only when all 16 gates pass:

```powershell
git add src/v5_2/labels scripts/freeze_phase2a_samples.py scripts/verify_phase2a_reference.py scripts/accept_phase2a.py tests/labels tests/governance/test_phase_1a_boundaries.py docs/reports/V5_2_PHASE_2A_ACCEPTANCE.md README.md
git commit -m "feat: complete Phase 2A reference label engine"
git push origin main
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

Require local HEAD equal to `origin/main` and GitHub `refs/heads/main`, with a
clean worktree. If any gate remains pending/failed, commit and push an honest
blocked acceptance report only if instructed; do not declare completion. In all
cases STOP and do not begin Phase 2B.
