# Checkpoint 18 — Gate V2 mutation ledger

These nine bounded mutations were run against the exact test targets below.
Result: `9 passed in 291.35s`, exit 0. The observations are the named gate's
source-pinned comparison or integrity predicate rejecting the mutation. They
are **not** a claim that the entire 18-gate evaluator was rerun once per
mutation. Unrelated gates were not evaluated on the mutated input and must
not be counted as either PASS or FAIL. The unmutated full evaluator is a
separate final verification.

| Mutation ID | Mutation / test | Expected failed gate | Observed failed gate predicate | Unrelated gates |
|---|---|---|---|---|
| M01 | Supported CA omitted; `test_supported_action_omission_is_detected_from_pinned_real_source` | `CORPORATE_ACTION_SAFETY` | `compare_ca_bundle_to_source` rejected the rehashed, incomplete action set | Not re-evaluated |
| M02 | Unsupported CA accepted; `test_real_ca_gate_evidence_is_exact_and_unsupported_types_fail_closed` | `CORPORATE_ACTION_SAFETY` | Exact evidence preserves rejection of rights issue, share conversion and stock split | Not re-evaluated |
| M03 | Full-day suspension changed to ordinary; `test_full_day_to_ordinary_mutation_fails_suspension_gate` | `SUSPENSION_SAFETY` | `compare_suspension_bundle_to_source` rejected the forged status | Not re-evaluated |
| M04 | Delisting boundary ignored; `test_delisting_effective_boundary_and_scoped_quarantine_are_exact` | `DELISTING_SAFETY` | Exact evidence distinguishes the correct `DELISTING_IN_HORIZON` result from ignored-boundary result; actual source scope remains quarantined | Not re-evaluated |
| M05 | Canonical identity / transition boundary altered; `test_wrong_canonical_or_transition_boundary_fails_identity_gate` | `IDENTITY_SAFETY` | `compare_identity_boundary_to_source` rejected both altered identity and effective boundary | Not re-evaluated |
| M06 | Premature `PENDING` → `AVAILABLE`; `test_rehashed_pending_to_available_without_h5_evidence_is_rejected` | `PENDING_MATURATION` | Independent H5 maturation comparison rejected the rehashed result | Not re-evaluated |
| M07 | `NOT_LABEL_SAFE` reasons swapped with identical aggregate counts; `test_count_preserving_reason_swap_changes_unsafe_evidence` | `NOT_LABEL_SAFE_PRESERVATION` | Exact row/reason evidence ID changed while count and reason totals remained equal | Not re-evaluated |
| M08 | Partition row membership swapped, preserving count; `test_partition_generation_requires_pinned_lineage_and_row_membership` | `PARTITION_INTEGRITY` | `verify_partition_generation_v2` rejected the different valid row | Not re-evaluated |
| M09 | Manifest active partition replaced by a separately valid, rehashed partition; `test_rehashed_valid_active_partition_swap_fails_frozen_expected_set` | `MANIFEST_INTEGRITY` | `verify_manifest_physical_exact` rejected the active set against frozen expected IDs | Not re-evaluated |

M02 and M04 have distinct evidence boundaries: the unsupported action types
are frozen contract negatives, and the delisting calculation comparison uses
a frozen Phase 2A contract fixture while the historical source region is
quarantined. Neither is being represented as a positive real-market label.

Command (from the isolated feature worktree, using the project virtual
environment):

```text
python -m pytest -q \
  tests/labels/test_phase2b_ca_safety_v2.py::test_supported_action_omission_is_detected_from_pinned_real_source \
  tests/labels/test_phase2b_ca_safety_v2.py::test_real_ca_gate_evidence_is_exact_and_unsupported_types_fail_closed \
  tests/labels/test_phase2b_suspension_safety_v2.py::test_full_day_to_ordinary_mutation_fails_suspension_gate \
  tests/labels/test_phase2b_delisting_safety_v2.py::test_delisting_effective_boundary_and_scoped_quarantine_are_exact \
  tests/labels/test_phase2b_identity_safety_v2.py::test_wrong_canonical_or_transition_boundary_fails_identity_gate \
  tests/labels/test_phase2b_maturation_gate_v2.py::test_rehashed_pending_to_available_without_h5_evidence_is_rejected \
  tests/labels/test_phase2b_unsafe_gate_v2.py::test_count_preserving_reason_swap_changes_unsafe_evidence \
  tests/labels/test_phase2b_gates_v2.py::test_partition_generation_requires_pinned_lineage_and_row_membership \
  tests/labels/test_phase2b_manifest_gate_v2.py::test_rehashed_valid_active_partition_swap_fails_frozen_expected_set
```

All nine expected target rejections were observed. No all-gates-auto-fail
shortcut was used. No pilot or provider request was executed.
