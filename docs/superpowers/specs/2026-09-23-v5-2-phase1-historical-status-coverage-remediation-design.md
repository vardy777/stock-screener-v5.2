# V5.2 Phase 1 Historical Status Coverage Remediation Design

Status: proposed; implementation is not authorized by this audit checkpoint  
Decision source: `V5_2_PHASE1_HISTORICAL_STATUS_AUTHORITY_AUDIT.md` outcome C

## Objective

Materialize a portable, content-addressed, lineage-bearing historical daily
security-status derivation authority from the already frozen raw payloads.
There must be zero network calls and zero provider requests.

## Immutable inputs

The implementation must exact-pin and verify before doing any work:

- panel `cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707`;
- manifest `d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0`;
- approval `ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07`;
- 118 exact raw payload hashes and 163 exact receipt hashes from that manifest;
- the three normalized component hashes and lifecycle hash from the panel;
- the exact approved calendar, PIT evidence, security-master approvals, request
  inventory, equivalence evidence, and current revocation set.

Missing, extra, changed, revoked, superseded, or non-reproducible input must
fail closed. No latest lookup is permitted.

## Minimal output

Create one content-addressed historical status derivation dataset. Each
identity/session result needed by the supported calendar must contain or
deterministically pin:

```text
canonical_security_identity
session
listed
risk_warning
full_day_suspended

lifecycle_component_id/hash
applicable_risk_interval_ids/hashes
applicable_suspension_observation_ids/hashes
closed_world_inventory_id

effective inputs
available_at inputs and derived available_at
StatusAvailabilityPolicyV2 ID

parent panel ID
parent approval ID
parent manifest ID
source version identity
derivation content hash / fact ID
```

For ordinary sessions, absence must be represented as a derivation over the
positive lifecycle component plus the exact closed-world ST and suspension
set/inventory hashes. Do not manufacture a provider observation saying
`ACTIVE`.

An interval-indexed immutable representation is allowed instead of physically
duplicating every security-session row, provided an arbitrary result has an
exact deterministic derivation ID and all referenced components are portable
and independently verifiable.

## PIT rules

- Lifecycle applicability follows the approved security-master authority.
- Date-only ST changes use the conservative next approved session at 16:30
  Asia/Shanghai unless a frozen stronger semantic applies.
- Full-day suspension semantics use the frozen `StatusAvailabilityPolicyV2`
  evidence; partial suspension never becomes full-day suspension.
- Acquisition timestamps never become historical `available_at`.
- Results after 2026-09-10 are outside this remediation scope.

## Governance outputs

Do not mutate any predecessor. Publish:

1. new content-addressed normalized/derivation facts;
2. exact coverage ledger with identity/session counts and explicit gaps;
3. deterministic replay evidence;
4. new source approval whose rules pin the derivation contract;
5. new DatasetManifest with exact fact hashes;
6. immutable supersession/composition evidence linking the old historical
   panel/manifest/approval and preserving the 71-row acceptance artifacts.

The new approval must not claim new provider coverage. It approves the
portable derivation representation of the already approved source version.

## Required tests

- exact reproduction of all four frozen component hashes;
- exact reproduction of the 118 raw and 163 receipt hash sets;
- ordinary status derivation pins closed-world negative evidence;
- ST enter/exit does not backdate knowledge;
- full-day versus partial suspension;
- listing and delisting boundaries;
- arbitrary covered identity/session produces stable derivation ID;
- missing/tampered/revoked/wrong-source component fails closed;
- post-coverage session fails closed;
- identical replay produces byte-identical facts, approval and manifest;
- provider request counter remains zero.

## Phase 2B bridge after remediation

Only after independent acceptance may a thin read-only adapter translate one
verified derivation result into `DomainLineageV1`. The adapter may package
frozen identities; it may not recalculate universe, lifecycle, ST, suspension,
or availability policy and may not select latest artifacts.

## Explicit non-goals

- no provider/network acquisition;
- no mutation of Phase 1 artifacts;
- no Phase 1 semantic change;
- no Phase 2A label semantic change;
- no Phase 2B Task 5 implementation or pilot in this checkpoint.

