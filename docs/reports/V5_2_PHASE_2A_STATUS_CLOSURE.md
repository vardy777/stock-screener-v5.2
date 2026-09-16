# V5.2 Phase 2A Checkpoint 5 — Nine-Session Status Closure

Status: `PASS / MANDATORY STOP BEFORE ASSEMBLER`

Starting HEAD: `2e4015a57fdcaa9d1d9a556c6b6fbc11b6ebe84a`

## Immutable evidence result

- Status Closure Audit ID: `7c62a4084090f4f672d69dc27fd8b04cd06f6369680c04b9d1b479e71683e25f`
- Existing approved Status evidence reused: `9 sessions / 5 payloads / 5 receipts`
- New Status provider requests: `0`
- Daily Bar provider requests: `0`
- Source approval reused: `60d31609f590cf08f54ff682d5c4de5a987cdb670b13fe33eeb2466389d39edc`
- PIT evidence reused: `aabfbcd3e8d4d03ff400c52a12ff005638b259bf0185e802d96372b4015f3f8f`
- New formal Phase 1 Status facts: `9`
- Supplement DatasetManifest: `fef0f11d8f23f59ef70759da20b8dedbce70331c48c1cf9c61468a202e22e46d`

All nine sessions are exact `suspend-d` rows with `suspend_type=S` and `suspend_timing=null`. Each raw payload and acquisition receipt passes content-hash verification and is already pinned by the existing approved Status manifest. `StatusAvailabilityPolicyV2` maps every full-day suspension to the historical D-close cutoff at `16:30 Asia/Shanghai`; acquisition time is ignored.

| identity | session | disposition | payload hash | receipt hash |
|---|---|---|---|---|
| 002166.SZ | 2019-04-12 | FULL_DAY_SUSPENSION | `4d5b7c85eb533b71079406388dc4a6687ace01267226921818dcdec152e4059a` | `af94dec1ac6ef3803945800f8d5e66b62bcf4a03ce8229433c62cab40ec98ba9` |
| 002166.SZ | 2019-04-16 | FULL_DAY_SUSPENSION | `4d5b7c85eb533b71079406388dc4a6687ace01267226921818dcdec152e4059a` | `af94dec1ac6ef3803945800f8d5e66b62bcf4a03ce8229433c62cab40ec98ba9` |
| 600155.SH | 2015-11-16 | FULL_DAY_SUSPENSION | `50dfc59ec000749ae9557d4cd7f30b4a2d5c85d5ac2aa7da6fe80ed0dba8fd0a` | `4a9d77706822c5696e48b19277f474157c909d982df29684c9cd8b252fb692a4` |
| 600155.SH | 2015-11-18 | FULL_DAY_SUSPENSION | `50dfc59ec000749ae9557d4cd7f30b4a2d5c85d5ac2aa7da6fe80ed0dba8fd0a` | `4a9d77706822c5696e48b19277f474157c909d982df29684c9cd8b252fb692a4` |
| 600155.SH | 2015-11-19 | FULL_DAY_SUSPENSION | `50dfc59ec000749ae9557d4cd7f30b4a2d5c85d5ac2aa7da6fe80ed0dba8fd0a` | `4a9d77706822c5696e48b19277f474157c909d982df29684c9cd8b252fb692a4` |
| 600155.SH | 2015-11-20 | FULL_DAY_SUSPENSION | `79eabb46adca197f2624dd6b3f99710d30188fb5cfefba719a280ad8cb871365` | `4eb534e4dbf26e4ab407a2243717dd7a1d7739a0af2ff161f57b222b23acf2e8` |
| 600155.SH | 2015-11-23 | FULL_DAY_SUSPENSION | `79eabb46adca197f2624dd6b3f99710d30188fb5cfefba719a280ad8cb871365` | `4eb534e4dbf26e4ab407a2243717dd7a1d7739a0af2ff161f57b222b23acf2e8` |
| 300131.SZ | 2014-09-11 | FULL_DAY_SUSPENSION / ANCHOR NOT_LABEL_SAFE | `d4ff7f80dcbdb25335a1c1ab927d679e0f38d79a52bfdf91bc74609ba69e1134` | `d8070be38df11bc6bd5ebf71ef88c370dde95e19a66e2d3d6c3b36ab054f8e87` |
| 002118.SZ | 2023-08-03 | FULL_DAY_SUSPENSION; not final tradable day | `d3c0fdaa5698e0d6289c1787437ade6132e87eee77a6f7942e4ab9a2ba8bfeb1` | `5b1557cc8b04e3dfdbef6a6ff56c1145797accf2addcfe9d4fe22f233c4611f0` |

The supplement is stored in an isolated Phase 1 namespace so it does not mutate the frozen Phase 1B-2A fact collection or change the Checkpoint 3 backfill inventory identity. Old Status artifacts remain unchanged. For `002118.SZ`, the approved Daily Bar payload ends on 2023-06-15 and exact full-day suspension observations cover every SZSE open session from 2023-06-16 through 2023-08-03; the immutable delisting boundary is 2023-08-04. The actual final trading session is therefore 2023-06-15.

## Recomputed frozen 22-slot audit

Evidence Gap Audit ID: `5547490f765385651c973590ac2e58bb152e5403462d35bb9195037956e6deb9`

```text
ASSEMBLER_LOOKUP_DEFECT = 22
REAL_PHASE1_EVIDENCE_ABSENT = 0
PROVEN_EXPECTED_ABSENCE = 14 sessions (9 suspension + 5 delisting boundary)
OTHER GAP = 0
BUNDLES CREATED = 0
5-SLOT PILOT = NOT RUN
```

`300131.SZ / 2014-09-11` has no legal D-close reference under the frozen contract and is explicitly carried forward as the `NOT_LABEL_SAFE` path for the future assembler. No price is synthesized. `002118.SZ / 2023-08-03` is proven suspended; the effective delisting boundary remains 2023-08-04, so no independent Daily Bar source is required for this checkpoint.

## Verification record

```text
focused Status closure / evidence-gap / root-cause / PIT tests
20 passed in 22.84s

full repository suite
645 passed in 119.42s

standalone / zero-project-dependency boundary
PASS forbidden imports: 0
PASS forbidden active paths/dependencies: 0
PASS prohibited repository inventory: 0
PASS phase 1a architecture boundary violations: 0

clean-room / build / wheel install / wheel smoke
build=true; install=true; wheel_smoke=true; zero_dependency_acceptance=true
580 passed, 65 skipped in 2.74s

credential sentinel scan
2 passed, 6 deselected in 68.36s

Status publication + evidence-gap deterministic replay
DETERMINISTIC_REPLAY=True

git diff --check
PASS (line-ending notices only; no whitespace errors)
```

Phase 2A remains `PENDING`. This checkpoint stops before Evidence Assembler and the five-slot pilot. Phase 2B remains blocked.
