# V5.2 Phase 1 Historical Daily Security Status Authority Audit

Date: 2026-09-23  
Mode: audit only; zero provider requests; zero network acquisition

## Decision

```text
C.
EXISTING HISTORICAL STATUS AUTHORITY = PARTIALLY SUFFICIENT

EXACT COVERAGE GAP =
the approved panel pins complete aggregate lifecycle, risk-warning, and
suspension sets, but the feature branch does not contain a readable,
lineage-bearing per-session fact/derivation artifact from which Phase 2B can
pin the exact source facts and available_at used for an arbitrary anchor.

NEW MATERIALIZATION FROM EXISTING RAW DATA = REQUIRED
NETWORK ACQUISITION = NOT YET REQUIRED
```

The historical authority is real and is not the 71-row acceptance sample.
Its governance chain and aggregate identities verify. The remaining defect is
an artifact-expression and distribution gap, not a proven provider-data gap.

## Frozen authority inventory

| Role | Immutable identity | Finding |
|---|---|---|
| Research-wide panel | `cd062ced913e865984d536bc85305f9c6e720e26cee111527aac120fd66fe707` | Aggregate interval/event contract and component hashes |
| Dataset manifest | `d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0` | 475,416 logical component rows, 5,551 identities, 2010-01-04 through 2026-09-10 |
| Source approval | `ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07` | `APPROVED_WITH_RULES`; supersedes the earlier 71-row approval |
| Equivalence evidence | `df531747996eab37b3b821e32ce2641a103f5e661006430ef3ee68ae1b2fea13` | Research-wide interval/event equivalence with the frozen 71/71 cross-source semantic evidence |
| Frozen-session resolution | `3ae79a145d7d0252aea1d5e35fb6b737fba568603cc5e2a9a499e22fdf68fd44` | Four acceptance sessions only; not an arbitrary-session fact store |
| PIT evidence | `aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f` | Pins `StatusAvailabilityPolicyV2` semantics |
| Cross-source evidence | `7aee446328623da71f2f0ca8ad3655399b8f7d389e4a71ea9304b075d3838cb9` | Prospective V2 71/71 semantic comparison |
| Evidence artifacts | seven artifacts, IDs beginning `2b339ac`, `312a754`, `4613be6`, `4b27628`, `66ae1a4`, `76a6e24`, `7c7d8f1` | All canonical identities verify and all have `PASS` status |

The 71-row manifest `57b4d38523c32a31959fb8dc9e2335778f97ed86562413c95e7ff9716ec65e3d`
is an acceptance-sample publication and predecessor authority. It is not the
research-wide arbitrary-anchor store.

## Mechanical identity verification

Canonical hash verification was performed with the repository's
`v5_2.data.identity.content_hash`, adding each artifact's frozen schema version
and excluding only its identity fields. Results:

```text
panel.verify                         PASS
frozen-session-resolution.verify    PASS
equivalence.verify                   PASS
evidence.verify (7/7)                PASS
approval.verify                      PASS
manifest.verify                      PASS
```

The approval ID is not present in any revocation artifact or the Phase 1B-2A
revocation registry. Its decision is `APPROVED_WITH_RULES`, and the manifest
pins the same approval ID and approval content hash. Revocation state at the
audited repository state is therefore valid.

The retained raw material in the main local checkout was audited read-only.
It exactly reproduces the frozen manifest and panel:

```text
raw payload hashes present / pinned       118 / 118, exact set match
receipt hashes present / pinned           163 / 163, exact set match
lifecycle rows                              5,551, hash match
namechange rows                              8,104, hash match
ST/risk-warning intervals                   1,677, hash match
suspension observations                   468,188, hash match
manifest logical row count                475,416, exact reconciliation
```

These raw and receipt files are not present in the current feature worktree.
Consequently they demonstrate that zero-network remediation is possible, but
they are not themselves a portable GitHub-readable Phase 2B authority.

## Meaning of the 475,416 rows

The manifest count is not a table of 475,416 explicit security-session status
facts. It is the sum:

```text
5,551 lifecycle intervals
+ 1,677 ST/risk-warning intervals
+ 468,188 suspend/resume observations
= 475,416 logical normalized components
```

`namechange` has 8,104 rows in the equivalence audit, of which 1,677 match the
frozen ST-name rule and enter the manifest row count. Suspension observations
contain 443,117 `S` and 25,071 `R` records; 2,644 `S` observations contain a
partial-session timing and are explicitly not classified as full-day
suspensions. The lifecycle set contains 333 identities with a delisting date.

The panel pins hashes for the canonical lifecycle, all namechange rows, the ST
subset, and all bounded suspension observations. It does not embed those rows,
their individual IDs, or a per-session derived fact table.

## Semantic authority findings

### Listing and delisting

Listing/delisting authority is the `stock-basic` lifecycle set composed from
the approved Phase 1B-1 and 2026 extension security-master lineages. The panel
pins its canonical `lifecycle_hash` and covers all 5,551 target identities.
The lifecycle resolves whether an identity is within `[list_date,
delist_date]`. Actual first tradable session is not proven by lifecycle alone;
where required it must be composed with the exact approved exchange calendar
and daily-bar authority. It must not be invented in the status layer.

### ST / risk warning

The ST authority is the canonical `namechange` set filtered by the frozen ST
name-prefix rule. Effective start/end dates define the interval. Because the
source lacks verified publication timestamps, the approval rule is
`date_only_same_close = NEXT_APPROVED_SESSION`. The `available_at` must be
derived with `StatusAvailabilityPolicyV2` and the exact approved calendar; it
must not use acquisition time or backdate the effective interval.

### Suspension

The suspension authority is the complete, terminal `suspend-d` request set
over the approved interval. `suspend_type=S` with empty `suspend_timing` is a
full-day suspension; partial-session observations are not full-day
suspensions; `R` is a resumption observation. The manifest pins the complete
request inventory, all raw payload/receipt hashes, `pagination_complete=true`,
coverage 2010-01-04 through 2026-09-10, and reports zero unresolved identities,
zero unresolved sessions, no coverage gaps, and no quarantine.

This is sufficient Phase 1 proof for closed-world absence within the exact
approved identity, date, request-inventory, and source-version boundary. It is
not a universal claim beyond that boundary.

### Ordinary status

Within the exact frozen coverage, ordinary status is a derived state:

```text
identity is inside the approved lifecycle
AND no PIT-visible ST interval applies
AND no full-day suspension observation applies to the session
```

The absence inference is legitimate only because the panel/manifest jointly
pin a complete terminal acquisition and zero-gap contract. Thus:

```text
ORDINARY STATUS DERIVATION = PROVEN WITHIN FROZEN COVERAGE
SUSPENSION CLOSED-WORLD PROOF = PROVEN WITHIN FROZEN COVERAGE
```

It still requires a derivation artifact that pins the positive lifecycle fact,
the closed-world suspension set/inventory, the ST set, the policy result, and
the governing approval/manifest. A bare boolean is not adequate lineage.

### Identity transitions

Canonical identity and identity-transition authority belongs to the approved
security-master/identity chain, not to daily security status. Status may
consume that identity for an effective session, but must not create a second
symbol-to-identity policy.

## HistoricalStatusRepositoryV1 audit

`HistoricalStatusRepositoryV1` is an incomplete calculation adapter, not a
self-verifying production authority. It accepts caller-supplied lifecycle,
risk-warning and suspension tuples and returns only:

```text
listed: bool
risk_warning: bool
suspended: bool
```

Positive properties are that it requires a timezone-aware cutoff, bounds the
lifecycle, and checks `available_at <= cutoff`. However, it does not load or
verify the panel, approval, manifest, raw hashes, source version, revocation
state, or closed-world acquisition. It returns no fact/evidence IDs,
`available_at`, content hashes, or derivation ID. Its `suspended = any(...)`
is safe only when the caller has already proved that `_suspensions` is the
complete frozen set. The class itself does not prove that precondition.

`security_status_repository.py` is a stricter generic four-dimension interval
resolver, but it is not wired to this research-wide panel and cannot substitute
for the missing exact historical materialization without an explicit pinned
bridge.

## Coverage

```text
coverage_start                         2010-01-04
coverage_end                           2026-09-10
approved open sessions                 4,055
historical target identities           5,551
logical normalized rows              475,416
lifecycle intervals                    5,551
ST/risk-warning intervals              1,677 (903 identities)
suspension observations              468,188 (4,657 identities)
delisting boundaries                     333
unresolved identities                      0
unresolved sessions                        0
declared coverage gaps                      0
quarantine count                            0
```

This supports the Phase 2B historical requirement only through 2026-09-10.
Anchors after that date are outside the audited authority and must fail closed
or use a separately approved incremental status authority.

## Phase 2B lineage sufficiency

The existing governance chain provides approval ID, manifest ID, aggregate
content hashes, source version, policy/evidence IDs, and a valid revocation
state. It does not currently provide, for an arbitrary identity/session, a
portable exact fact/derivation ID and the actual `available_at` inputs/result.

```text
PER-SESSION FACT ID AVAILABLE       NO
AVAILABLE_AT AVAILABLE              DERIVABLE, NOT MATERIALIZED/PINNED PER RESULT
CONTENT HASH AVAILABLE              AGGREGATE SET HASHES ONLY
APPROVAL LINEAGE AVAILABLE          YES
MANIFEST LINEAGE AVAILABLE          YES
REVOCATION VALIDATION AVAILABLE     YES AT AUDITED STATE
PHASE2B EXACT LINEAGE POSSIBLE      YES AFTER ZERO-NETWORK REMATERIALIZATION
```

Therefore an arbitrary-anchor `DomainLineageV1(daily_security_status)` cannot
yet be constructed without either relying on non-portable raw state or
fabricating a per-session fact ID. Task 5 must remain stopped.

## Verification commands

All commands were read-only except creation of this report/design:

```text
content-hash audit of panel/resolution/equivalence/evidence/approval/manifest
  PASS (12/12 artifacts)

existing-raw reconstruction audit
  PASS: 118 raw hashes, 163 receipt hashes, four component hashes exact

revocation search
  PASS: audited approval absent from every repository revocation artifact

provider requests
  0

network acquisition
  0
```

The minimal remediation design is frozen separately in
`docs/superpowers/specs/2026-09-23-v5-2-phase1-historical-status-coverage-remediation-design.md`.

