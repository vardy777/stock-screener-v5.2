# V5.2 Phase 2B Checkpoint 18 — Master lineage hard stop

## Decision

```text
CHECKPOINT 18 = FAIL / OPEN
STEP 1 FIVE-DOMAIN PRODUCER = INCOMPLETE
DAILY BAR EXACT-FACT ADAPTER = IMPLEMENTED / FOCUSED TESTED
REAL SOURCE-PINNED MONTH = NOT RUN
18-GATE ACCEPTANCE = NOT CLAIMED
PILOT = NOT AUTHORIZED / NOT RUN
PROVIDER REQUESTS = 0
```

The accepted historical Daily Bar fact authority at feature HEAD
`b8f4e00bb1019871af709c26b3ed61336181b3d4` removes the Daily Bar
membership blocker. This attempt added a read-only Phase 2B adapter over
`HistoricalDailyBarFactReaderV1.load_exact`. It records only actually consumed
`DailyBarFactV1.fact_id` values and pins the authority, membership set,
derived approval and manifest, coverage ledger, composition, replay, and
parent governance chain. Missing bars remain absent, not classified.

The next required input is a separately verifiable approved Master/Identity
effective interval for each candidate. The currently pinned complete Master
manifest `025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b`
contains exactly three `fact_content_hashes`:

```text
968ae9660ae02f4a1e16a8eb6510a62368e44defc7f99f7ed56714364c722386
016d9b64bb0cda79583a06eb2cc1c89c7b8668e3d63a354b44a159668dd8975f
2675dc691521dbcfecc3ac48c8ef3af1e3fb69a9230afb6835c9a3a0ad86e69a
```

The historical and complete fact bundles contain ordered security-identity
memberships, not each identity's listing/delisting interval. The 2026 universe
extension contains a baseline symbol list plus 74 effective changes, not the
full 2010–2025 interval table. The historical bundle references two
`effective_identity_graph_ids`, but a search of the repository-local data
artifacts found those IDs only as references inside that bundle, not as
independently readable graph bodies. The approved Status portable authority
does contain lifecycle intervals, but the frozen bridge requires an
**independent approved Master/Identity chain** before consuming them. Treating
the Status lifecycle as the Master proof would collapse two required domains
into one source and manufacture an independent verification that does not
exist in this runtime.

This is a representation/evidence-availability gap, not a demonstrated
incorrect market datum. It must not be repaired by reading provider raw
payloads at Phase 2B runtime, copying symbol strings into intervals, defaulting
ACTIVE, changing frozen eligibility rules, or fabricating Master fact IDs.
No month partition, manifest, candidate census, preregistration, or formal gate
PASS was produced.

## Bounded diagnostics

```text
rg -l '"list_date"|"effective_from"|"intervals"' \
  data/phase_1b_exit_remediation/governance \
  data/phase_1b1_2026_extension/governance
```

Only the unrelated status-equivalence artifact contains a match in those
scoped governance directories. Repository-local `data/**/*.json` searches
for each of the two graph IDs returned only the historical Master fact bundle.
The complete Master manifest's three fact IDs and the extension's 74 changes
were read directly from their content-addressed JSON artifacts.

## Resume requirement

Provide an already-approved, physically readable, exact-pinned Master/Identity
interval artifact if one exists, **or** explicitly authorize a narrow one-time
portable representation of the already-approved Master truth, with independent
source binding, content-addressed row membership, approval/manifest lineage,
revocation handling, and no provider request. It must be reviewed before this
five-domain producer can claim a real source-pinned month. The frozen Phase 1
business semantics and Phase 2A Label Engine must remain unchanged.

## Verification

```text
.venv/Scripts/python.exe -m pytest -q tests/labels/test_historical_daily_bar_lineage.py
  4 passed
.venv/Scripts/python.exe -m pytest -q tests/labels/test_historical_daily_bar_lineage.py tests/data/test_historical_daily_bar_authority.py
  12 passed (before the clean-room skip marker was added to the real-artifact cases)
.venv/Scripts/python.exe -m pytest -q
  910 passed, 1 skipped in 550.03s
.venv/Scripts/python.exe scripts/verify_standalone.py
  PASS; forbidden imports, active paths, repository inventory, architecture
  boundary, and Phase 2B feature/label firewall violations all 0
.venv/Scripts/python.exe scripts/clean_room_acceptance.py
  first concurrent run: FAIL, 1 failed / 730 passed / 180 skipped;
  existing tests/providers/test_acquisition_controls.py::test_rate_limiter_serializes_concurrent_callers
  asserted >=0.024s while observing 0.015s under concurrent full-suite load
.venv/Scripts/python.exe scripts/clean_room_acceptance.py
  isolated rerun: PASS, 731 passed / 180 skipped; build, wheel install/smoke,
  zero-dependency acceptance all true; archive findings empty
git diff --check: PASS
Credential-pattern scan of the three changed files: no matches
```

Checkpoint 19 pilot, broad run, and Phase 3 remain blocked.
