# V5.2 Phase 1A Exit Acceptance

Acceptance date: 2026-09-06 (Asia/Shanghai)

Tested implementation commit: `4bb4fca859015442729689806806dec53c11a1ca`

## Scope

This acceptance covers only the credential-free provider, immutable acquisition,
evidence, source-approval, PIT-policy, normalization, manifest and governance
frameworks. All approval artifacts exercised by tests use synthetic provider and
dataset identities. No real Tushare token, real provider network call, real
historical ingestion or real dataset approval was used.

## Fresh verification evidence

```text
.\.venv\Scripts\python.exe -m pytest -q
121 passed in 0.45s

.\.venv\Scripts\python.exe scripts\verify_standalone.py
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

.\.venv\Scripts\python.exe scripts\clean_room_acceptance.py
clean_room_dependencies = true
clean_room_install = true
clean_room_tests = true (121 passed in 0.55s)
build = true
archive_findings = none
wheel_install = true
wheel_smoke = true
old_pythonpath_removed = true
zero_dependency_acceptance = true
```

The clean-room runner explicitly removes both `PYTHONPATH` and `TUSHARE_TOKEN`
from the inherited environment. Provider behavior is tested only through
injected transports. The AST verifier rejects direct network-client imports and
research imports of provider, credential, acquisition, checkpoint, raw and
normalization boundaries.

## Gate decision

```text
PROVIDER FRAMEWORK = PASS
SOURCE APPROVAL FRAMEWORK = PASS
CREDENTIAL SAFETY = PASS
RAW / REVISION IDENTITY = PASS
CHECKPOINT / RESUME = PASS
RATE LIMIT / RETRY = PASS
NORMALIZATION BOUNDARY = PASS
PIT AVAILABILITY POLICY = PASS
DATASET MANIFEST = PASS
GOVERNANCE = PASS
CLEAN-ROOM = PASS
DETERMINISTIC REPLAY = PASS

HISTORICAL PIT DATA = FAIL
REAL DATASET APPROVALS = NONE
READY FOR REAL SOURCE AUDIT = YES
READY FOR LABEL ENGINE = NO
```

## Gate rationale

- Request identity hashes only canonical logical request fields and excludes all
  credentials and acquisition clocks.
- Provider payload identity and acquisition receipt identity are separate;
  acquisition-time-only changes do not create provider revisions.
- Checkpoint resume verifies its own content hash, request/policy compatibility
  and every referenced raw payload before continuing.
- Evidence artifacts, approvals and revocations are immutable and content
  addressed. Resolution requires source, dataset kind, requested coverage and
  `resolution_as_of`; ambiguity fails closed.
- Evidence validity uses evidence-type-specific, versioned rules. Missing,
  failed, stale, conflicting and incompatible evidence cannot approve.
- Date-only announcements become available no earlier than the next verified
  exchange-session close. Historical backfill acquisition time is never mapped
  to historical `available_at`.
- Dataset manifests pin the exact `approval_id`, approval content hash and
  approval resolution time. Later approval or revocation artifacts do not
  mutate or dynamically reinterpret an old manifest.
- Deterministic replay with identical logical provider responses produces equal
  payload hashes, normalized output and checkpoint hash across different
  acquisition times; only receipt identity changes.

## Frozen boundary after acceptance

Phase 1A authorizes only Phase 1B real-source auditing. It does not authorize
formal historical ingestion, publication of approved V5.2 facts, features,
labels, ranking, ML, strategy research, trading or broker access. Every real
dataset kind remains independently unapproved until its own evidence and source
approval process passes.
