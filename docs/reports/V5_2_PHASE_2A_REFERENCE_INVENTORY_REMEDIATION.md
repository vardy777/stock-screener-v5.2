# V5.2 Phase 2A Checkpoint 8 — Reference Inventory Remediation

CHECKPOINT 8 = STOP / REAL REFERENCE SAMPLE UNAVAILABLE

V1 INVENTORY ID = 81bd6df1955b9e18831779bd7274947f7da6dca50d5554f94cf7d85da31ac1c9
V1 FILE SHA-256 = 795bdcfd9117339fd6d85fa293b5514e4fb9da71a850286e1b0d8c870d6fbda7
CHECKPOINT 7 NEGATIVE ACCEPTANCE ID = 84d61057ecf5f527dcb5067fe0ea2b6103edf0f66388535e8ceeffd3ef10c3c8
APPLICABILITY AUDIT ID = 236039b2286afaff54017317ceeedc08b8e4c40a5a94a676256167c85d96f4d4
REPLACEMENT DISCOVERY ID = 947a8cd54a0a9a9bf91a8a4b45e7b502c272fb8dff374eab19b99615fca98f48
PREDICATE VERSION = phase2a-reference-stratum-predicates-v1
DISCOVERY ALGORITHM VERSION = phase2a-approved-evidence-discovery-v1

## Five-slot applicability audit

| slot | registered stratum | old sample | actual immutable-evidence behavior | failed frozen criterion | discovery status | reason |
|---:|---|---|---|---|---|---|
| 16 | expected future bar missing | 000969.SZ / 2024-06-05 | states=['LABEL_AVAILABLE']; required H1..H5 bars are complete | no approved exchange-open future session lacks both a bar and a valid explanation | REAL_REFERENCE_SAMPLE_UNAVAILABLE | FROZEN_REFERENCE_STRATUM_INCOMPATIBLE_WITH_PHASE1_APPROVED_EVIDENCE_CONTRACT |
| 17 | unsupported corporate action | 000651.SZ / 2010-07-12 | states=['LABEL_AVAILABLE']; corporate_actions contain no unsupported action type | no RIGHTS_ISSUE, STOCK_SPLIT, or SHARE_CONVERSION exists in the label window | NOT_SEARCHED_AFTER_MANDATORY_CONTRACT_CONFLICT | STOP_BOUNDARY_TRIGGERED_BY_SLOT_16 |
| 20 | lower barrier first | 000969.SZ / 2024-02-07 | barriers=(('hit_3pct_before_-2pct', 'UPPER_FIRST', '2024-02-08'), ('hit_5pct_before_-3pct', 'UPPER_FIRST', '2024-02-08')) | target barrier contract is UPPER_FIRST, not LOWER_FIRST | NOT_SEARCHED_AFTER_MANDATORY_CONTRACT_CONFLICT | STOP_BOUNDARY_TRIGGERED_BY_SLOT_16 |
| 21 | neither barrier | 000969.SZ / 2024-03-01 | barriers=(('hit_3pct_before_-2pct', 'LOWER_FIRST', '2024-03-05'), ('hit_5pct_before_-3pct', 'NEITHER', '')) | at least one target barrier contract has a decisive hit | NOT_SEARCHED_AFTER_MANDATORY_CONTRACT_CONFLICT | STOP_BOUNDARY_TRIGGERED_BY_SLOT_16 |
| 22 | same-session double-barrier ambiguity | 000969.SZ / 2024-02-08 | states=['LABEL_AVAILABLE']; reasons=[]; barriers=(('hit_3pct_before_-2pct', 'LOWER_FIRST', '2024-02-19'), ('hit_5pct_before_-3pct', 'LOWER_FIRST', '2024-02-20')) | no same-session upper-and-lower ambiguity occurs before a prior decisive hit | NOT_SEARCHED_AFTER_MANDATORY_CONTRACT_CONFLICT | STOP_BOUNDARY_TRIGGERED_BY_SLOT_16 |

## Contract conflict

Slot 16 requires a valid approved five-domain bundle that simultaneously contains an exchange-open future session with no approved bar, no suspension, no delisting explanation, and valid identity. The frozen Phase 1 assembler rejects precisely that unexplained absence before bundle construction. Therefore a normal approved bundle cannot reproduce this stratum without weakening Phase 1 correctness.

Result: `FROZEN_REFERENCE_STRATUM_INCOMPATIBLE_WITH_PHASE1_APPROVED_EVIDENCE_CONTRACT`.

Inventory V2 was not created. No supersession artifact was created. Slots 17/20/21/22 were not searched after the mandatory STOP condition, preventing open-ended or outcome-selected replacement search.

PROVIDER REQUESTS = 0
NETWORK CALLS = 0
PHASE 2A = FAIL / OPEN
READY FOR PHASE 2B = NO
PHASE 2B STARTED = NO

## Verification

- remediation focused tests: `4 passed in 5.20s`
- Phase 2A label tests: `116 passed in 56.78s`
- Phase 0–1C regression: `501 passed in 98.59s`
- full pytest: `681 passed in 155.89s`
- standalone / zero-project-dependency checks: PASS; four finding counts are zero
- clean-room: PASS; `586 passed, 95 skipped in 2.94s`
- build, install, wheel smoke: PASS; archive dependency findings empty
- V1 inventory and Checkpoint 7 negative acceptance diffs against Checkpoint 7 HEAD: empty
- deterministic replay: PASS; identical IDs and output on both runs (expected fail-closed exit code `2`)
- credential sentinel scan: configured credential values present `0`, findings `0`; no credential value was printed
- `git diff --check`: PASS
