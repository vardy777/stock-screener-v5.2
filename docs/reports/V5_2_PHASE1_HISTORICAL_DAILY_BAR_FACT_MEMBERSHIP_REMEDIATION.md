# V5.2 Phase 1 Historical Daily Bar Fact Membership Remediation

## Scope and disposition

This checkpoint creates a portable, immutable row-level representation of the
already-approved historical Daily Bar truth. It does not change source coverage,
market values, identity/normalization/unit/availability policy, or Phase 2A label
semantics. It does not authorize Checkpoint 18, a pilot, or Phase 2B resumption.

```text
PHASE1 HISTORICAL DAILY BAR FACT MEMBERSHIP REMEDIATION = PASS / FROZEN
SOURCE COVERAGE CHANGED = NO
SEMANTICS CHANGED = NO
PROVIDER REQUESTS = 0
NETWORK ACQUISITION = 0
CHECKPOINT 18 = FAIL / OPEN
CHECKPOINT 18 RESUME READY = AWAITING CHATGPT REVIEW
```

## Frozen parent and source preflight

```text
baseline feature HEAD = 1cdf28656f4946aa8b6edb0d74460f5dd9e680ac
parent panel = a618046c952a9bb863a1ec93fcc4d79c24cfca69542fdbb1c6581c1fde75a31d
parent approval = eaa2c254b85077ae8f988c393b133ba90f5443025d2cfdbe10523229f8f753f4
parent manifest = cb79850fac1c28e7b1e8bd9991d65c26f61add832b2f5ed67c40c586a13fd8c6
source binding = 176dba27d4cb6943e2434f1608668dc5bc756fa2e1357e18098927873032f3e8
source content set = de95192812d99f1c7f4e4363b8160a1b8728d76f503aa7edbf5c851a719527bb
availability evidence = 2bb3877daa164b5c09b617c9a44168d1a8035fae6e247ef4cb023d313070448e
coverage = 2010-01-04 .. 2026-09-10
raw payloads = 5,884 / 5,884 exact hashes; missing/extra/duplicate/tampered = 0
receipts = 5,914 / 5,914 exact hashes; missing/extra/duplicate/tampered = 0
```

The named source checkout was used once as read-only input to the offline
rematerializer. The runtime reader opens only the physical portable corpus in
this repository; it has no source-checkout, junction, raw-payload, or provider
fallback. Source preflight verifies the complete raw inventory before processing
any row. Receipt acquisition times are not used as historical `available_at`.

## Reconstruction and coverage

The materializer reuses `DailyBarFactV1`, the frozen normalizer and identity
classifier, and `NEXT_SESSION_SAFE`. OHLC remains unadjusted; volume and amount
use the frozen ×100 shares and ×1000 yuan conversions, without rounding.

```text
expected / reconstructed observed rows = 14,010,422 / 14,010,422
expected / reconstructed source symbols = 5,483 / 5,483
requested effective symbol-sessions = 14,433,604
missing unclassified symbol-sessions = 423,182
coverage ratio = 0.970680780767
excluded non-target rows = 52,466
duplicate fact IDs = 0
duplicate security-session keys = 0
invalid identities = 0
unresolved facts = 0
quarantined facts = 0
coverage gaps = 423,182 (missing bars remain missing, not inferred suspension)
Phase1B-2B corrected overlap = 2,481,310 / 2,481,310 rows
overlap fact-ID mismatches = 0
overlap semantic mismatches = 0
```

Frozen sample-session counts and sorted-symbol hashes for 2012-06-29,
2018-06-29, 2025-06-30, and 2026-06-30 match the parent panel exactly. The
approved calendar maps the 2026-09-10 coverage edge to 2026-09-11 16:30
Asia/Shanghai. No D@15:00 fact or acquisition timestamp is research-visible.

## Portable authority and governance

```text
fact authority = 12ea218b47389979561423a2289791bfe504040b4bbe6d667af26967dad55933
membership set = 8bdc8afccebe33b7918a2751a4c08c3ed51fe50bc334d1409557606a9397645d
coverage ledger = 632484c08fb7e9e24f59bbb33129dcabaf192b80529c35eaffceed731893508d
derived approval = 834d20964081575ec758abc3f28584b35ff414ac347a04e028d86ecf9752a656
derived manifest = 232a5ebaece1a8c3552ccb4c9bdebd40048afae19c6086f246aa377c9235e546
representation composition = c2ebb472773fe595cb87703ec03bf6206bacddb3cd34eb68576176ae3d518482
replay evidence = 0abffb860b3f4de201c5fd24431c4905b9e7ce5e1707fa59bc5b5fd902b0772c
shards = 201 monthly, 1,660,219,157 compressed bytes
facts = 14,010,422
```

Each shard has deterministic gzip bytes, a storage hash, uncompressed content
hash, row count, coverage bounds, and an ordered fact-ID membership hash. The
authority commits the ordered monthly membership hashes and the exact 5,884
source payload hashes. Writes are create-or-identical. The derived approval's
scope is explicitly a portable representation of the parent truth, not a new
provider approval or new observation. The parent approval is not revoked.

Two complete rematerializations from identical frozen input bytes had equal
observation and shard-descriptor hashes:

```text
run 1 / run 2 observation hash = d479c60332ec9563d7d3736ee8c7d031c03fd5501021f3672581bfaf3025c5db
run 1 / run 2 descriptor hash = be97b0a1907cfe83010ec0df2e21b5bdb09a5e87222221b5be64e62a2e33bb66
complete runs = 2
deterministic replay = PASS
```

The exact portable reader independently validated governance and read the
112,075-row January 2024 month index without the source checkout. It resolved
`000001.SZ / 2024-01-02` with `available_at=2024-01-03 16:30 +08:00` and
`000001.SZ / 2026-09-10` with `available_at=2026-09-11 16:30 +08:00`.
Research `resolve()` requires exact derived approval and manifest pins; month
and H5-bounded reads do not load the full historical corpus.

## Verification commands and results

```text
COMMAND: python scripts/rematerialize_historical_daily_bar_membership.py
         --source-main C:\Users\lisha\stock-screener-v5.2
RESULT: two complete runs; 14,010,422 rows, 5,483 symbols, 201 shards,
        2,481,310 exact corrected-overlap facts; immutable authority,
        governance and replay evidence published offline.

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
RESULT: 906 passed, 1 skipped in 894.75s (0:14:54).
        The skipped historical Status reconstruction test requires an explicit
        offline Status staging root; it is outside this Daily Bar remediation.

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
         tests/data/test_historical_daily_bar_authority.py
         tests/data/test_historical_daily_bar_materialization.py
         tests/data/test_historical_daily_bar_governance.py
RESULT: 17 passed in 0.38s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
         tests/data/test_daily_bar_facts.py
         tests/data/test_daily_bar_source_binding.py
         tests/data/test_phase_1b_exit.py
         tests/data/test_historical_lineage_composition.py
         tests/real_audits/test_daily_bar_availability.py
         tests/real_audits/test_phase_1b_exit_runtime.py
         tests/refresh/test_daily_bar_composite_lineage.py
RESULT: 65 passed in 4.63s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
         tests/labels/test_dataset_contracts.py
         tests/labels/test_partition_store.py
         tests/labels/test_anchor_enumerator.py
         tests/labels/test_partial_maturation.py
         tests/labels/test_phase2b_firewall.py
         tests/labels/test_phase2b_coverage.py
         tests/labels/test_phase2b_gates.py
RESULT: 67 passed in 0.83s

COMMAND: .\.venv\Scripts\python.exe -m pytest -q
         tests/labels/test_phase2a_acceptance.py
         tests/labels/test_phase2a_pilot.py
RESULT: 11 passed in 7.95s

COMMAND: .\.venv\Scripts\python.exe scripts/clean_room_acceptance.py
RESULT: PASS; clean-room dependencies/install/tests, build, wheel install/smoke,
        zero dependency and old-PYTHONPATH isolation passed;
        730 passed, 177 skipped in 5.19s; archive findings = none.

COMMAND: .\.venv\Scripts\python.exe scripts/verify_standalone.py
RESULT: PASS; forbidden imports/paths/dependencies/repository inventory = 0;
        Phase1A and Phase2B boundary violations = 0.

COMMAND: git diff --check
RESULT: PASS on all 215 staged files, including 201 portable shards.

COMMAND: credential scan of new code and governance
RESULT: PASS; case-insensitive scan for credential/token/header markers in
        new Python files and governance JSON found no matching files. Portable
        shards contain only the fixed DailyBarFactV1 fields, not raw responses.
```

The focused negative tests cover missing/extra/wrong-hash raw input, wrong
normalizer/unit version, D@15:00 substitution, corrected-overlap mismatch,
missing/extra/tampered shards, duplicate membership, wrong exact pins,
revocation, unknown/out-of-coverage lookup, and tampered parent/derived
governance. They do not use a network provider.

## Stop boundary

```text
PHASE1 SEMANTIC CHANGE = NO
PHASE2A SEMANTIC CHANGE = NO
CHECKPOINT 18 = FAIL / OPEN
PILOT = BLOCKED
PHASE2B TASK 12 / BROAD RUN = NOT STARTED
origin/main = unchanged
```

Resume Checkpoint 18 only after independent GitHub review of this feature
branch and the portable corpus.
