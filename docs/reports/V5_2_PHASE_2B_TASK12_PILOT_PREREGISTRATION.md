# V5.2 Phase 2B Task 12 — Pilot preregistration (no pilot run)

This is a preregistration, not pilot acceptance. Checkpoint 19, Phase 3, and
pilot calculation remain unauthorized. The exact content-addressed artifacts
are held in the private, Git-ignored `data/` store; this public record contains
identities and aggregate counts, not source payloads or label outcomes.

## Frozen source census

- Census ID: `1a1f2465a2d60e84f61874feccf6538c1c1daec3f69369600255d78379285a8d`.
- Approved-source candidate-set hash: `76ed7e266c91e0dcef1326555b3c1fae08d47e0530c4a97f7fd381292f655770`.
- Window: 2010-01-04 through 2010-01-29; 34,271 effective anchor candidates.
- Source-pinned counts (strata may overlap): ordinary control 24,636;
  excluded before label 6,950; supported cash dividend 5; supported bonus
  share 0; unsupported corporate action 0; full-day suspension 2,258;
  delisting boundary 0; identity transition 0; not-label-safe source
  conditions 1,169; pending maturation 0.
- Absent strata: `SUPPORTED_BONUS_SHARE`, `UNSUPPORTED_CA`,
  `DELISTING_BOUNDARY`, `IDENTITY_TRANSITION`, `PENDING_MATURATION`.
  These are **ABSENT**, not silently replaced by samples from a different
  period or by outcome-based selection.

## Immutable Task 12 contract

- Preregistration ID: `5a5d9aa9f72a00e63a5712cf6f6f0bed23823119641a563ff68ea141e808dccc`.
- Selection rule: `FIRST_SOURCE_ORDERED_CANDIDATE_PER_STRATUM_V1`.
- Four distinct candidates selected from present strata; anchor sessions
  2010-01-04 and 2010-01-08. The private exact artifact pins their candidate
  IDs. No label result was consulted or produced.
- The contract pins the five approved domain authorities (Calendar, Master,
  Daily Bar, Status, Corporate Action), Phase 2A semantic authority
  `75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7`,
  maturation authority
  `28b090531ece57fd41548e31eaa819cb02f7669f3fd8802a84d75b0a6f654fc9`,
  private corpus manifest
  `0489978b34834817ee0e33dbd46d4e90b86a14e9827f89ba5b93433797c2ddd6`,
  CAS inventory
  `a559e02eb8726289bb19c80daa37f78c8041e58bf6884d6c92c382da91ab6536`,
  Gate V2 contract
  `6a0eb73c468c44b96cded8781503bbf1e8304fc6f94d81e544675f144eba609c`,
  and Gate V2 evaluator
  `77eb5c4f897189c81322c39ff6bc487716052f773c1b72f6d6e49d858751540c`.
- Frozen pilot acceptance predicates: `NO_PROVIDER_REQUESTS`,
  `EXACT_FIVE_DOMAIN_LINEAGE`, `18_GATES_PASS`, `DETERMINISTIC_REPLAY`,
  `ZERO_MISMATCH`.

The census was rederived from the exact approved five-domain producer and
frozen month-coverage candidate set. Preregistration rederived the census
again before accepting it. Exact readers check canonical bytes and IDs;
create-or-identical writers reject collisions. This work executes **no pilot**.
