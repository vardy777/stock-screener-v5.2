# V5.2 Phase 2A V2.1 Final Acceptance

## Scope and authority

This is the fresh final acceptance required by Checkpoint 15.  It is not a
restatement or transformation of the V2.1 infrastructure evaluation.  The
final verifier reloaded the exact immutable inputs, reconstructed the typed
acceptance inputs, checked canonical bytes for every pinned infrastructure
artifact, independently invoked the literal resolver twice, and only then
created the final acceptance artifact.

```text
V2.1 design head       = a66825e25d40a46eceae18a50f1f2535ab9ee975
V2.1 amendment         = d4a7941e2583eb84dd1bf501fb9183d5346f3813f383704b691c3798fb8ac25b
Attempt 2 plan         = d9cfcf4822bd0d617e1e599e35fde0b939de03cd
Frozen infrastructure  = 6e436f5da10fc9d2ba5825897f209f018e35d5bf
Supersession           = 37279c7e92bd33891c833eb95dae1cfc4d104388acc03f01d0ee810f216b390c
```

The exact infrastructure artifacts are:

```text
fadd791ac0562cf218a6e52954c36eff05244d6b69e7a70cb38814b256fb98d5
da6356776020f8d32737184bbd7759e3ecdee49ce8dc67784fe4dda3d9840ec4
161f59093ac9e9949de007bf08989e1220b8a2177991a604ad48cee2c70428a4
5d4cfa298891ad0cf1f2e997429d7e2f505a97f63e66acc9e8a9970ad1c16f4f
fe268e2d080580485715bb69eefc4c6ebc144b959c404ff0f50692be12d685bb
edf35f614c2631b352b47c5680354b86e517a23f7ae620fa0d285a3ec90f407c
```

## Final immutable acceptance artifact

```text
schema                 = Phase2AAcceptanceV2_1
acceptance ID/hash     = 75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7
artifact path          = data/phase_2a/v2_1_final_acceptance/
                          final-phase2a-acceptance-v2-1-75df8940cfa5f31757fc9b105be172e60581ead32ff0494fb4c84a2baac43cf7.json
deterministic replay   = PASS (two fresh resolver evaluations agree)
collision behavior     = PASS (existing bytes must be identical; differing bytes raise)
```

All sixteen literal gates independently resolve to `PASS`:

```text
LABEL CONTRACT                 PASS
CAUSAL ISOLATION               PASS
TRADING SESSION SEMANTICS      PASS
RETURN SEMANTICS               PASS
MFE/MAE SEMANTICS              PASS
BARRIER SEMANTICS              PASS
CORPORATE ACTION SAFETY        PASS
SUSPENSION SAFETY              PASS
DELISTING SAFETY               PASS
IDENTITY SAFETY                PASS
MISSING DATA FAIL-CLOSED       PASS
LABEL_PENDING                  PASS
NOT_LABEL_SAFE                 PASS
REFERENCE SAMPLES              PASS
INDEPENDENT VERIFICATION       PASS
DETERMINISTIC REPLAY           PASS
```

The final verifier also checked the two required fail-closed boundaries from
the exact V2.1 inputs:

```text
missing-bar base evidence      = REAL_MARKET_EVIDENCE
missing-bar fixture            = DETERMINISTIC_CONTRACT_FIXTURE
missing-bar observed           = false
missing-bar rejection          = UNEXPLAINED_MISSING_BAR:2024-01-25
missing-bar engine calls       = 0

unsupported CA condition       = 002029.SZ / 2012-05-08 / UNSUPPORTED_SHARE_CONVERSION
unsupported CA rejection point = CorporateActionRepository.query
unsupported CA rejection       = NOT_RESEARCH_SAFE: unsupported action type
unsupported CA engine calls    = 0
```

## Fresh verification results

```text
V2.1 final/focused suites      = 80 passed in 180.39s
labels regression              = 221 passed in 261.18s
Phase 0-1C data/refresh/provider regression = 299 passed in 1.58s
full pytest                    = 786 passed in 368.00s
replay/tamper/revocation/firewall/predicate suite = 48 passed in 152.86s
credential/governance suites   = 18 passed in 21.87s
standalone                     = PASS (0 forbidden imports, paths, inventory, or Phase 1A boundary violations)
clean-room/build/install/wheel smoke = PASS (616 passed, 170 skipped in 3.38s)
clean-room zero dependency     = PASS
credential scan                = PASS; .env ignored and untracked; no production credential pattern
AST/import isolation           = PASS
immutable input canonical-byte checks = PASS
provider/network requests      = 0
git diff --check               = PASS
```

The only changes relative to the frozen infrastructure commit are the final
acceptance artifact, the final verifier, its materializer, its TDD tests, and
this final-acceptance plan/report.  No Phase 1 source/provider/data lineage,
label engine, evidence assembler, Attempt 1 data, or Attempt 2 data was
modified.

## Closure

```text
PHASE 2A              = PASS / CLOSED
READY FOR PHASE 2B    = YES
PHASE 2B STARTED      = NO
origin/main update    = NO
PR / merge            = NO
```

This checkpoint ends after the feature-branch publication and remote-head
verification.  Phase 2B remains unstarted pending independent review.
