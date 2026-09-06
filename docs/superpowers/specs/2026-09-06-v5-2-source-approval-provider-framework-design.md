# V5.2 Source Approval and Provider Framework Design

## Scope

This design covers the first independently reviewable slice of V5.2 Phase 1:

1. provider abstraction;
2. credential-safe Tushare client interface;
3. credential-free acquisition/import contracts;
4. immutable raw artifact storage;
5. deterministic normalization boundary;
6. PIT availability validation;
7. coverage and revision audits;
8. dataset-kind-scoped SourceApprovalArtifact;
9. DatasetManifest publication;
10. provider/framework tests.

It does not acquire real data, accept a real token, approve any dataset kind,
implement the full Security Master/status/bar/action/financial schemas, or
authorize research, features, labels, ranking, ML or trading.

## Frozen trust architecture

```text
Primary acquisition source       = Tushare Pro
Authoritative verification       = SSE / SZSE official records
Optional daily-bar cross-check   = BaoStock
Research truth                   = V5.2-owned immutable PIT facts
```

A provider is never approved globally. Each dataset kind has its own evidence,
policy version and decision:

```text
daily_bar
trade_calendar
security_master
daily_security_status
corporate_action
financial_disclosure
historical_delisting
```

Allowed decisions are `APPROVED`, `APPROVED_WITH_RULES`, `PENDING` and
`REJECTED`. Only the first two permit publication into the approved fact zone.
`APPROVED_WITH_RULES` must carry machine-enforced restrictions such as date
bounds, excluded fields, mandatory cross-source sampling or conservative
availability rules.

## SourceApprovalArtifact

`SourceApprovalArtifactV1` is an immutable derived decision, not a hand-written
trust root. It contains:

```text
approval_id
schema_version
source_name
dataset_kind
decision
coverage_start
coverage_end
verified_at
verification_method
license_or_usage_note
source_version_identity
policy_version
rule_set
evidence_ids
evidence_bundle_hash
evaluator_version
supersedes_approval_id  # optional
```

The evaluator accepts only immutable evidence artifacts produced by registered
audits. Required evidence categories are coverage, PIT/time-field validation,
revision behavior, historical sample audit, content identity, license/usage
documentation and any dataset-specific cross-source verification. Missing,
failed, stale, conflicting or tampered evidence produces `PENDING` or
`REJECTED`; callers cannot pass `approved=True`.

Approval identity is the canonical content hash of the decision payload.
Changing evidence, rules, coverage, provider version or policy creates a new
artifact. Old approvals remain readable and are never edited to express a
revocation or supersession.

Revocation is itself an immutable artifact:

```text
SourceApprovalRevocationArtifactV1
  revocation_id
  approval_id
  reason
  effective_at
  created_at
  evidence_ids
  policy_version
  content_hash
```

The approval resolver requires explicit `source_name`, `dataset_kind`, requested
coverage and `resolution_as_of`. It deterministically returns one exact
`approval_id`, or fails closed if no unique applicable approval exists. It
applies only revocations effective on or before `resolution_as_of` and follows
explicit `supersedes_approval_id` links; creation order or repository iteration
order never decides the result. A later approval or revocation cannot change the
historical meaning of an already published manifest because the manifest pins
the resolved `approval_id` and its resolution context.

## Package boundaries

```text
src/v5_2/providers/
  contracts.py       # requests, pages, client protocol, sanitized errors
  credentials.py     # environment/.env lookup; returns SecretStr-like handle
  rate_limit.py      # deterministic injected clock/sleeper limiter
  retry.py           # bounded transient retry and backoff policy
  tushare.py         # transport adapter only; token never enters values/logs

src/v5_2/data/
  raw_artifacts.py   # immutable token-free raw envelope and content hash
  checkpoints.py     # request/page completion state and resume validation
  normalization.py   # registered dataset-kind normalizer protocol
  availability.py    # dataset-kind PIT availability policies
  validation.py      # schema/PIT/revision validation evidence
  coverage.py        # requested-versus-observed coverage evidence
  source_approval.py # evidence evaluator and approval repository
  manifests.py       # DatasetManifest from approved normalized facts
  pipeline.py        # acquisition -> raw -> validate -> normalize -> publish
```

Research modules may import only approved fact repositories and
`DatasetManifest`; they cannot import `v5_2.providers`, raw cache, credentials or
pipeline transport types. An AST governance test enforces this direction.

## Credential boundary

The only supported token name is `TUSHARE_TOKEN`. `credentials.py` may read the
process environment and an explicitly supplied, repository-local, untracked
`.env` file. It never searches parent/sibling directories. The token is wrapped
in an opaque credential object whose `repr` and `str` are redacted.

The token is used only while constructing the outbound authenticated provider
call. It is prohibited from:

- request dataclasses and request IDs;
- URLs, logs, exception messages and retry diagnostics;
- raw response envelopes and HTTP debug dumps;
- checkpoints, manifests and approval artifacts;
- pytest parameters, fixtures and output.

Tests use a sentinel token and scan captured output, exceptions and all written
files to prove the sentinel never appears. Real tokens are never used in tests.

The repository ignores `.env`, `.env.*`, `credentials*`, `secrets*` and raw
provider cache directories. A tracked `.env.example` may contain only
`TUSHARE_TOKEN=` with an empty value.

## Provider and acquisition contracts

`ProviderRequestV1` contains `source_name`, `dataset_kind`, `endpoint`,
canonical non-secret parameters, requested fields, page size and request policy
version. Its deterministic `request_id` is the canonical hash of exactly those
fields. Requested fields and parameters have canonical ordering and encoding.

Credentials and all volatile wall-clock or transport observations are forbidden
from `request_id`, including `requested_at`, `received_at`, retry timestamps,
acquisition timestamps and transport timing. The same logical historical
request therefore has the same `request_id` whenever it is executed.

`ProviderPageV1` is the transport result used before persistence. Persistence
separates provider payload identity from the acquisition observation. No
normalizer receives a live client.

`HistoricalProviderClient` exposes one method:

```python
fetch_page(request: ProviderRequestV1, credential: Credential) -> ProviderPageV1
```

The Tushare adapter maps a registered dataset kind to an allowlisted API name.
Arbitrary API names are rejected. Parameters are canonicalized before request
identity is computed. The adapter must accept an injected transport in tests.

Pagination continues until a page is shorter than the requested limit or a
dataset-specific terminal rule fires. Repeated page identity, non-advancing
offset, provider row-limit ambiguity or unexpected ordering fails closed.

Rate limiting uses an injected monotonic clock and sleeper. Retry is bounded,
uses deterministic exponential backoff from a versioned policy, and retries
only classified transient transport/rate-limit failures. Authentication,
schema, permission and provider business errors fail immediately with sanitized
messages.

## Immutable raw cache and checkpoints

The raw zone stores one canonical provider payload artifact per provider page:

```text
raw/<source>/<dataset_kind>/<request_id>/<page_identity>/<payload_hash>.json
```

`RawPayloadArtifactV1` contains request ID, canonical page identity, canonical
provider payload, semantic provider metadata and `payload_hash`. Semantic
metadata may affect interpretation of the payload but excludes acquisition time,
attempt counts and transport timing. `payload_hash` is the canonical content
hash of logical request/page identity, canonical provider payload and semantic
provider metadata.

`AcquisitionReceiptV1` separately contains `payload_hash`, `acquired_at`,
attempt/transport metadata and `receipt_hash`. Receipt identity may change for a
later acquisition, but it cannot change payload identity.

The same logical request/page plus the same canonical provider payload always
produces the same `payload_hash`, regardless of acquisition time. It is an
idempotent reacquisition, not a provider revision. The same logical request/page
with a different canonical provider payload produces a new `payload_hash` and a
revision observation. A different payload written to an already-addressed
immutable path is a collision and fails closed.

Checkpoints contain the ordered raw artifact IDs already accepted, next offset,
policy versions and a checkpoint content hash. Resume first revalidates every
referenced artifact and request parameter. A changed request, missing page,
hash mismatch or non-contiguous page sequence invalidates the checkpoint.

## Normalization and approved fact zones

Normalization is a pure registered function:

```python
normalize(raw_artifact, normalization_policy) -> tuple[NormalizedRecord, ...]
```

It performs no network, credential, filesystem or approval lookup. Output order
is canonical and independent of provider row order. Duplicates, missing keys,
ambiguous code mappings, numeric coercion loss or unregistered fields fail
closed. Dataset-specific fact construction is deferred to the corresponding
Phase 1 slice.

Raw and normalized staging facts are not research truth. The pipeline publishes
approved V5.2 facts only after resolving a dataset-kind approval and enforcing
its coverage/rule set. Research paths cannot address staging directories.

## PIT availability policy

Provider fields describe different clocks and are never interchangeable:

- `trade_date`/session is an economic observation date, not availability.
- `end_date`/period_end is an accounting period, never availability.
- `ann_date` is a calendar publication date, not proof of intraday availability.
- `f_ann_date` or another provider field is not trusted until independently
  validated for that endpoint/version.

Each dataset kind registers an `AvailabilityPolicyV1` with field semantics,
timezone, provider release behavior, cutoff rule and validation evidence ID.
The derived `available_at` is accompanied by `availability_policy_version` and
source fields used in the derivation.

For date-only announcements with no verified release time, the fact is not
available to same-date D-close research. The conservative default makes it
eligible no earlier than the close of the next verified exchange session.
Unknown calendar mapping or missing announcement date fails closed.

Daily market rows use the session as event time but may be available only after
the dataset-kind publication SLA. The policy uses the later of the verified
publication boundary and recorded acquisition time for live ingestions.
Historical backfills must use an audited conservative rule; backfill ingestion
time itself cannot masquerade as historical availability.

## Validation evidence

Every audit emits an immutable evidence artifact with input IDs, code/policy
version, sample selection, counts, findings and content hash. Its machine-readable
validity fields include at least:

```text
evidence_type
observed_at
verified_at
policy_version
source_version_identity
input_artifact_ids
valid_until  # optional
```

Staleness is evaluated by a versioned `EvidenceValidityPolicy`, not an arbitrary
global age threshold. The policy defines deterministic rules separately for
historical immutable coverage evidence, provider/API behavior evidence,
PIT/time-semantics evidence, license/usage evidence and cross-source evidence.
Rules may use `valid_until`, provider/source-version changes, policy-version
compatibility, input replacement or evidence-type-specific review intervals.
Missing, failed, stale, conflicting or tampered evidence always fails closed.

Registered evidence categories are:

- coverage: requested dates/symbols versus present, duplicate and missing rows;
- PIT/time fields: endpoint documentation plus sampled official/event records;
- revisions: repeated snapshots or known amended disclosures, append behavior;
- historical samples: boundary dates including listing/delisting, ST,
  suspension, holidays and corporate actions as applicable;
- cross-source: deterministic symbol/date/value matching with tolerances;
- license/usage: documented allowed research/storage behavior and review date;
- content: raw and normalized hashes with reproducibility replay.

Fixtures may validate evaluator mechanics but can never approve a real dataset
or support `HISTORICAL PIT DATA = PASS`.

## DatasetManifest

`DatasetManifestV1` contains `dataset_id`, schema version, creation time,
the exact pinned `approval_id` and approval `resolution_as_of`, exact coverage,
row/symbol counts, date bounds, ordered
raw/normalized/fact content hashes, normalizer and availability-policy versions,
quality findings and PIT validation status.

Manifest creation rejects `PENDING`/`REJECTED`, uncovered rows, rule violations,
hash mismatch, ambiguous duplicates, partial pagination and non-PASS PIT status.
The manifest never contains credentials or grants approval.

## Test and acceptance strategy

TDD covers credential redaction, exact endpoint allowlisting, canonical request
IDs, pagination termination and loop detection, retry classification/backoff,
rate limiting, checkpoint resume/tamper rejection, immutable raw collisions,
row-order-independent normalization, conservative date-only availability,
evidence completeness, dataset-kind isolation and manifest fail-closed rules.
It also covers deterministic request identity across execution times; identical
reacquisition, changed-payload revision and acquisition-time-only changes;
approval supersession, immutable revocation, `resolution_as_of` and old-manifest
reproducibility; and deterministic stale/non-stale outcomes for each registered
evidence validity rule.

Clean-room acceptance installs the package without a token and runs all tests.
Secret scans use a sentinel and verify stdout/stderr, exceptions, raw artifacts,
checkpoints, approvals and manifests. Network tests use injected transports;
there is no real Tushare call in this slice.

## Phase 1A exit

Phase 1A may report the provider framework complete only when all local,
governance and clean-room tests pass. It must still report:

```text
HISTORICAL PIT DATA = FAIL (no approved real dataset)
READY FOR REAL SOURCE AUDIT = YES
READY FOR LABEL ENGINE = NO
```

Real Token use and dataset-kind audits require a separate execution step. The
token is placed by the user in the environment or untracked `.env`; it is never
requested in chat.
