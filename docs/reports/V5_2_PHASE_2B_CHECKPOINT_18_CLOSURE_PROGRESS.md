# V5.2 Phase 2B Checkpoint 18 Closure Remediation — Interim Record

## Status

`CHECKPOINT 18 = FAIL / OPEN`. This record does not replace or amend
`V5_2_PHASE_2B_CHECKPOINT_18_HARD_STOP.md`. No pilot, broad materialization,
or Phase 3 work was performed. The 18-gate V1 evaluator is now explicitly
fail-closed: caller-authored equal hashes can no longer generate a formal PASS.
This is a safety repair, **not** a completed independent evidence model.

## Verified facts and remaining work

- The accepted portable status resolver is present. Its lifecycle rows are
  reconstructed from immutable security-master payloads and checked against
  the frozen status panel lifecycle hash. The production month reader must
  still verify the independent approved master/identity chain before using
  those intervals; the status resolver alone is not an identity authority.
- The approved corporate-action facts bundle contains 39,407 supported facts
  (`CASH_DIVIDEND` 38,880; `BONUS_SHARE` 527). The existing materialization
  audit contains 7,894 `UNSUPPORTED_SHARE_CONVERSION` quarantines. A production
  reader must pin and consume the quarantine ledger, not equate absence of an
  approved fact with absence of an unsupported event.
- No production five-domain artifact-to-`HistoricalEvidenceWindowV1` producer
  exists yet. No real month materialization or source-pinned census was run.
- No independently derived evidence contract for all 18 formal gates exists
  yet. The legacy evaluator now returns `FORMAL_EVIDENCE_MISSING` for every
  gate until the replacement is implemented and verified. No 18/18 claim is
  made.
- Task 12 preregistration is not complete. Its selection must wait for a real
  source-pinned census, as specified in the closure directive.

## TDD and verification actually run

1. Added a regression showing equal caller-authored hashes must not yield a
   formal semantic PASS. RED result: 1 failed, 23 deselected; the old evaluator
   returned `all_pass=True`.
2. Changed the V1 evaluator to fail closed for formal acceptance. Focused
   command: `.\\.venv\\Scripts\\python.exe -m pytest -q tests/labels/test_phase2b_gates.py`
   → `24 passed`.
3. Full command: `.\\.venv\\Scripts\\python.exe -m pytest -q`
   → `889 passed, 1 skipped in 454.31s`. The skip is the existing explicit
   offline status staging-root requirement.
4. `git diff --check` → no whitespace errors.

No provider request or data network acquisition was made. These tests verify
the interim fail-closed safety patch only; they do not establish Checkpoint 18
acceptance. The next implementation step is the exact-pinned five-domain
producer, followed by real month integration, gate-specific independent
evidence, bounded census, preregistration, and the full closure verification.
