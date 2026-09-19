# V5.2 Phase 2B Maturation Contract Audit

## Scope

Checkpoint 16R audits the frozen Phase 2A maturity contract only. It makes no
Phase 1 change, no Phase 2A semantic change, no Phase 2B materialization, and
no network/provider request.

## Frozen contract proof

`LabelState` is a field of `LabelValueV1`; `LabelResultV1` is an ordered tuple
of seven independent `LabelValueV1` objects. `LabelValueV1.create` validates
the state of that individual label. It does not impose an all-values-equal
constraint.

`ReferenceLabelEngine.evaluate` resolves `(H1, H3, H5)` and emits values in
frozen `CORE_LABELS` order. Its exact mapping is:

```text
return_1d                    -> H1
return_3d                    -> H3
return_5d                    -> H5
max_favorable_excursion_5d   -> H5
max_adverse_excursion_5d     -> H5
hit_3pct_before_-2pct        -> H5
hit_5pct_before_-3pct        -> H5
```

For each label it emits `LABEL_PENDING / HORIZON_NOT_COMPLETED` exactly when
that label's mapped horizon has not completed. Existing frozen regression
`tests/labels/test_reference_engine.py::test_one_day_available_while_five_day_labels_pending`
asserts this mixed-state behavior.

## Immutable-evidence behavioral audit

The audit used the existing accepted Layer-A real-market Slot 4 bundle, not a
provider call or synthetic market fact:

```text
SOURCE SLOT       = 4 (LIMIT-UP-LIKE_PATH)
SOURCE BUNDLE ID  = 8a212db4e0337eaceaf90ddf167ce9b278cd9adde05c584f826a6006c99125fa
ANCHOR            = 000969.SZ / 2024-09-30
H1 / H3 / H5      = 2024-10-08 / 2024-10-10 / 2024-10-14
AUDIT FIXTURE ID  = 72ebcd53c5e3e54745c1e775431d3c4846f80ac0c26324bad8a70101f33b2c6b
RESULT ID         = 9ed55533beaf04b1fa1bf492178c6e6550a6526507b733b9eacb8aa3f7588259
```

The fixture is a deterministic offline reconstruction of the exact source
bundle with only `latest_completed_session = H1`; all bars, status, corporate
actions, identity, calendar, and five-domain lineage are copied from the
immutable source bundle. No source evidence was altered.

```text
RETURN_1D          = LABEL_AVAILABLE (0.07464213)
RETURN_3D          = LABEL_PENDING / HORIZON_NOT_COMPLETED
RETURN_5D          = LABEL_PENDING / HORIZON_NOT_COMPLETED
MFE_5D             = LABEL_PENDING / HORIZON_NOT_COMPLETED
MAE_5D             = LABEL_PENDING / HORIZON_NOT_COMPLETED
3/-2 BARRIER       = LABEL_PENDING / HORIZON_NOT_COMPLETED
5/-3 BARRIER       = LABEL_PENDING / HORIZON_NOT_COMPLETED
```

Both barrier calculations had `UPPER_FIRST` with decisive session
`2024-10-08` (H1), yet both emitted `LABEL_PENDING`. Therefore:

```text
LABEL STATE GRANULARITY             = PER LabelValueV1
FIELD_LEVEL_MATURATION SUPPORTED    = YES
BARRIER EARLY MATURATION SUPPORTED  = NO
```

The two barrier values become available only when their frozen H5 endpoint is
completed. The engine may calculate a path before then internally, but it does
not expose an early barrier result.

## Phase 2B design consequence

`LabelRowV1` remains only an immutable envelope around the exact frozen result:
it cannot promote, collapse, or derive availability and has no row-level state.
The correct `MATURED_PENDING_ANCHORS` selector is value-level:

```text
select prior pending LabelValueV1 when its frozen maturity endpoint
is <= latest approved completed exchange session

H1: return_1d
H3: return_3d
H5: return_5d, MFE_5d, MAE_5d, both barriers
```

This is not a new semantic rule. It records the engine's already frozen output
contract. Maturation continues to create a new `LabelResultV1`, `LabelRowV1`,
partition generation, and manifest; old artifacts remain immutable.

```text
FROZEN PHASE2A CONTRACT             = LabelValueV1 / LabelResultV1 / ReferenceLabelEngine
PHASE2B DESIGN CHANGED              = YES, wording only
DESIGN CHANGE SUMMARY               = cites frozen field-level proof and H5 barrier maturity
PHASE1 CHANGE                       = NO
PHASE2A SEMANTIC CHANGE             = NO
PHASE2B IMPLEMENTATION STARTED      = NO
CHECKPOINT 16R                      = PASS / READY FOR INDEPENDENT REVIEW
```
