# V5.2 Checkpoint 20 — Phase 3 Feature Contract and Causal Firewall Design

Status: `PROPOSED FOR INDEPENDENT REVIEW`. This document freezes no new
runtime authority until reviewed. Checkpoint 20 is a design checkpoint; it
does not authorize feature computation, a historical feature dataset, or an
Alpha conclusion.

## Purpose and authority

Phase 3 builds a reproducible description of what was knowable for a security
at a fixed D-close research boundary. Phase 4 may later join that description
to future labels under a separately preregistered evaluation. The intended
Phase 3 outcome is an immutable feature dataset with verified causal inputs,
independent calculation, coverage accounting, and deterministic replay.

The design starts at feature-branch parent
`917e39f2c5182310ccb10cef08acde3ab68d128d`. Its Checkpoint 19 public
acceptance ID is
`3f390b57a058fbc00864088f490903db64a4da1f9eb0afc1d5a13f3f3b9debb0`;
the exact Task 12 preregistration is
`5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc`.
The frozen Phase 1 approvals, coverage, availability policies, revocations,
Phase 2A label semantics, and Phase 2B label materialization remain the source
of authority. This design does not reinterpret them.

Checkpoint 19 establishes a four-case engineering pilot. It is not a test of
factor effectiveness. Phase 3 must not inspect label values, future returns,
barriers, or Alpha metrics while selecting or revising Feature Set V1.

## Approaches considered

| Approach | Advantage | Cost or risk | Decision |
| --- | --- | --- | --- |
| Compute every feature from the anchor D bar | Conventional D-close definitions | Approved historical D bars can become available only at the next safe session; using them at D 16:30 leaks knowledge | Reject as a default |
| Use only facts actually available by D 16:30, with explicitly lagged price feature names | Preserves the frozen research clock and makes historical coverage honest | Some D-ending features will be unavailable | Select |
| Move the feature clock to D+1 or 20:00 | May increase usable bars | Changes the frozen anchor decision and its relation to the label | Defer to a separately approved contract |

The selected approach makes a feature's observation endpoint explicit. It
never silently substitutes D−1 for a feature whose definition ends on D.

## Anchor, cutoff, and allowed information

An observation key is `(canonical_security_identity, exchange-open
as_of_session D, feature_name, feature_version)`. The knowledge cutoff is
**16:30 Asia/Shanghai on D**, matching the frozen historical D-close research
boundary. A fact may contribute only if its verified `available_at <= cutoff`
and its effective/session semantics apply to the claimed observation period.
For a window, every constituent fact and every applicable corporate action
must pass this test. A backfill acquisition timestamp cannot establish
historical knowledge time.

The historical approved Daily Bar authority currently requires next-safe-
session 16:30 availability for its reconstructed bars. Consequently an
approved D close can be a legal label reference while it is **unavailable**
for a feature evaluated at D 16:30. Such a feature receives
`UNAVAILABLE_AT_CUTOFF`. An explicitly defined `lag1_*` feature may end at
D−1 when its D−1 facts are available by D's cutoff. These are different
feature versions and cannot share one name or silently replace each other.

Allowed input domains for the first baseline set are approved Calendar,
Master/Identity, Daily Bar, Daily Security Status, and Corporate Action facts,
with exact immutable approvals, manifests, coverage and revocation state.
Historical anchors consume approved Phase 1 lineage and need no invented
`ResearchDataSnapshot`. A real contemporaneous snapshot may be pinned when it
exists. Financial disclosures are outside the first baseline set; adding
them requires an explicit later feature-set revision.

Forbidden inputs are D+1 or later bars/status/actions/identity or universe
membership; future publication or revision observations; Phase 2 label rows,
label bundles, label reference prices, future returns, MFE/MAE, barrier
outcomes, and Phase 4 research results. The feature producer receives no
provider, raw acquisition, mutable latest pointer, or network capability.

## Feature definitions and result contract

Checkpoint 20 defines the envelope and safety rules. The exact 10–15
baseline feature definitions and versions are a later, separately frozen
Feature Set V1. Candidate categories are 1/3-session reversal, 5/10/20-
session momentum, 5/20-session realized volatility, volume and amount ratios,
and high-low position or amplitude. Initial historical price definitions
should use visibly named lagged endpoints, such as `lag1_momentum_5d_v1`.
Each definition must freeze its exchange-session lookback, observation
endpoint, treatment of suspension, cash dividends and bonus shares,
denominator/zero rules, units, decimal precision, and independent reference
formula before observing any label relationship. A session count is an
approved exchange-open count, not a natural-day or security-tradable count.

`FeatureValueV1` is an immutable result envelope with at least:

```text
feature_name, feature_version
canonical_security_identity, as_of_session
knowledge_cutoff, observation_end_session, lookback_session_ids
input_fact_ids, input_authority_ids, interval_evidence_ids
calculation_policy_id
value | null, state, reason | null
content_hash
```

`content_hash` is the canonical hash of schema version and all semantic
fields. IDs, input ordering, decimals, timezone and reason strings have
versioned canonical encodings. Requested-at, acquired-at, retry and wall-
clock timing cannot enter identity. `value` is present only for `AVAILABLE`;
zero is a legitimate computed value, never a missing-value substitute.

States have separate meanings:

| State | Meaning | Value |
| --- | --- | --- |
| `AVAILABLE` | All inputs and interval absence proofs were valid at cutoff | Computed decimal |
| `UNAVAILABLE_AT_CUTOFF` | An otherwise relevant fact became known after D 16:30 | `null` |
| `INSUFFICIENT_HISTORY` | The frozen lookback extends before approved effective history | `null` |
| `PENDING_EVIDENCE` | Required exact evidence or approval is currently missing or unresolved | `null` |
| `NOT_FEATURE_SAFE` | Contradiction, unsupported action, ambiguous identity, tampering, revocation, or unproven missing bar makes computation unsafe | `null` |

Later acquisition cannot turn a fact known only after D's cutoff into an
`AVAILABLE` D observation. A legitimate new governance artifact may supersede
an observation only if it proves different historical knowledge, with old
observations and manifests retained. Pending evidence never implies zero.

## Price and corporate-action safety

Price features use approved unadjusted raw bars plus only corporate-action
facts and revisions known by the cutoff. A return or volatility lookback
crossing a cash dividend or bonus share uses a frozen, causally reconstructed
historical wealth path. Provider adjusted prices and future-vintage factors
are not feature inputs. Independent calculation must reproduce cash and share
effects without calling the production feature calculation.

The supported action types are exactly those in the pinned scoped approval.
Rights issues, stock splits and share conversions remain unsupported until
their own approval. For any affected security-period, unsupported action,
coverage gap, quarantine, or inability to prove *no applicable event* yields
`NOT_FEATURE_SAFE` or `PENDING_EVIDENCE` according to the proven condition.
An empty query result alone is not a no-action proof. A provider-side endpoint
cannot substitute for independent approved coverage.

A proven full-day suspension explains a missing bar but does not create a
synthetic close, volume or zero return. Each feature definition must say
whether that window is unsafe or whether an explicitly approved economic
mark rule applies. The initial simple price and activity features take the
conservative unsafe path if an endpoint or necessary trade observation is
absent. An unexplained missing bar fails closed. Identity transitions require
the approved canonical chain over the whole lookback; symbol equality is
insufficient. Delisting and the frozen five-session IPO seasoning rule retain
their upstream meanings.

## Producer, calculation, and causal firewall

The later `FeatureInputBundleV1` will contain only cutoff-filtered, verified
facts, explicit no-event/coverage evidence, exact domain lineage, and the
frozen definition ID. The offline assembler validates each input before
constructing the bundle. `ReferenceFeatureEngine` is a pure deterministic
function of that bundle and returns `FeatureValueV1` values. It receives no
repository handle, clock, filesystem path, environment variable, or provider
client. The independent calculator receives the same verified semantic
inputs but cannot import or call production feature calculations.

`v5_2.features` must not import `v5_2.labels`, Phase 2 label artifacts, or
future-outcome helpers. AST/import and dependency-graph checks cover direct
and indirect imports; sentinel tests reject field names and fixtures that
carry label or future values into feature production. Runtime mutation tests
insert future-dated facts, late revisions, revoked approval, wrong-domain
lineage, and tampered coverage; each must be rejected before calculation.
The Phase 4 feature/label join is a separate read-only consumer of two exact
manifests, never a dependency of the feature producer.

## Materialization, replay, and quality

The first engineering validation month is proposed as `2010-01`, because its
Phase 2B census and lineage are already understood. It is an engineering
month, not an Alpha sample. Before its outcomes are viewed, Phase 3B/C must
freeze the exact Feature Set V1, candidate census, month, applicable coverage,
numeric quality thresholds, and independent comparison method.

Feature partitions are immutable anchor-month generations, canonically
ordered by `(as_of_session, canonical_security_identity, feature_name,
feature_version)`. A partition records complete state/reason counts, exact
input lineage set, row count and content/storage hashes. Create-or-identical
is idempotent. A newer generation supersedes rather than edits the old one.
`FeatureDatasetManifestV1` pins the exact feature-set ID, contract version,
active partition IDs, governance lineage, coverage intervals/gaps, exclusion
counts, supersession map, and previous manifest ID. Research requires an
exact manifest ID, never a latest-directory scan.

Validation reports coverage and missing/unsafe rates by feature, session,
security and reason; cross-sectional distributions, extreme/duplicate/
constant values and unusual jumps; independent recalculation results;
mutation results; and two-run replay IDs. Quality problems may quarantine
scoped rows or block a feature/partition. A headline coverage percentage
cannot erase a systematic gap. The 2010-01 exercise cannot establish full
2010–2026 research coverage; the historical dataset expands only to intervals
with actually approved, materialized, PIT-safe lineage.

## Phase 3 acceptance gates

The following are proposed machine-enforced predicates. Checkpoint 20 accepts
their **contracts**, not runtime PASS results. Each runtime gate must persist
its input artifact IDs, predicate version, outcome and failure reason.

| No. | Gate | Required proof |
| --- | --- | --- |
| 1 | `FEATURE_CONTRACT_PINNING` | Exact feature-set/version and definition hashes |
| 2 | `KNOWLEDGE_CUTOFF` | Every used fact `available_at <= D 16:30`; endpoint explicit |
| 3 | `CAUSAL_ISOLATION` | AST/dependency and sentinel checks exclude all label/future inputs |
| 4 | `INPUT_LINEAGE` | Exact approved, immutable, nonrevoked domain artifacts and coverage |
| 5 | `CORPORATE_ACTION_SAFETY` | Supported actions and no-action interval proof; unsupported scope rejected |
| 6 | `SUSPENSION_SAFETY` | Proven missing bars distinguished from unexplained absence; no synthetic trade |
| 7 | `IDENTITY_SAFETY` | Canonical chain, effective interval and upstream eligibility hold |
| 8 | `MISSING_DATA_SEMANTICS` | Missing and unavailable values remain `null` with reasons |
| 9 | `FEATURE_STATE_SEMANTICS` | State/value/reason invariants and cutoff permanence hold |
| 10 | `INDEPENDENT_RECALCULATION` | All accepted real-month values and states match independent result |
| 11 | `DETERMINISTIC_REPLAY` | Two exact pinned runs produce identical IDs and counts |
| 12 | `PARTITION_INTEGRITY` | Canonical membership, bytes, hashes and create-or-identical behavior |
| 13 | `MANIFEST_INTEGRITY` | Active partitions, scope, lineage and supersession verified across artifacts |
| 14 | `INCREMENTAL_IDEMPOTENCY` | Same inputs produce no new generation; changed authority produces scoped supersession |
| 15 | `CLEAN_ROOM_STANDALONE` | Install/build/wheel smoke, no sibling project, no private data in Git |

All 15 runtime gates must PASS before historical feature publication. A
missing or failed gate is not counted as PASS. Gate code must derive its
result from verified artifacts rather than literal success values.

## Execution sequence and stop boundary

1. Review and freeze this Checkpoint 20 design. No feature engine is
   implemented during this checkpoint.
2. Write and review a Phase 3 implementation plan. Resolve every formula,
   state transition, authority and quality threshold before a real run.
3. Implement the contract/firewall and pure reference/independent engines by
   TDD; freeze a modest Feature Set V1 before inspecting outcomes.
4. Run the preregistered 2010-01 engineering month, compare independently,
   mutate boundaries, replay and audit quality. Publish only accepted scope.
5. Expand historical materialization and seek Phase 3 final acceptance. Only
   afterward write a separate Phase 4 Alpha-study preregistration and join
   exact feature and label manifests for evaluation.

Checkpoint 20 exits with an independently reviewed design, precise
implementation plan entry criteria, and `READY_FOR_FEATURE_IMPLEMENTATION`
only after design acceptance. It does not imply `15/15 PASS`, historical
feature coverage, Alpha, production readiness, or permission to use ML.
