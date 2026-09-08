# Phase 1B-2A Evidence Sufficiency Policy Proposal V1

Status: **PROPOSED — NOT ADOPTED**. This proposal is forward-looking. It does not modify the frozen 61-entry contract, change any old disposition, approve the dataset, or authorize publication.

## Why the frozen contract cannot currently close

The original contract requires every frozen entry to resolve as an independent match. Thirty of the `ordinary` entries were selected by prioritizing later-delisted identities while assigning the fixed session 2025-01-02. Twenty-nine had already delisted between 2003 and 2024, so an independent exact-session trading/status record cannot exist. This is a systematic sample-applicability defect, not evidence that the provider values disagree. One remaining ordinary entry is ST on that date in both provider and independent data; its earlier unresolved result was a mapping error caused by treating the stratum label as a value.

The identity-transition case was also a mapping issue: BaoStock retrospectively labels 2025-02-14 with the new code, while the SZSE-hosted implementation notice establishes that 300114 applies through T-1 and 302132 begins on 2025-02-17. The official chain controls PIT identity.

Current frozen ledger: 32 MATCH, zero MISMATCH, zero UNRESOLVED, and 29 INDEPENDENT_EVIDENCE_UNAVAILABLE. The old contract is therefore not satisfied and remains immutable.

## Evidence distribution and risk

- Ten ST/risk-warning entries independently match across 2018-2025.
- Ten suspension entries independently match across 2013-2018.
- Five unique delisting-effective events appear twice each and independently match across 2013-2024.
- One ordinary entry matches in 2025 after correcting the stratum/value mapping.
- One identity transition matches the official effective chain in 2025.
- Twenty-nine post-delisting ordinary entries cannot test active ordinary status and provide no dataset-level equivalence assurance for that semantic.

This evidence supports the daily observable meaning of ST state, full-day suspension, and the sampled delisting-effective boundaries. It does not establish complete equivalence for active ordinary status, actual listing, ST exit, resumption-notice knowledge, or all historical publication-time semantics. Those semantics must remain PENDING. Facts relying on unsupported announcement-time knowledge must remain unpublished; next-session-safe derivation may be used only where the existing availability policy permits it.

## Proposed prospective replacement contract

If accepted by ChatGPT, freeze a new inventory before retrieving results. Do not replace or erase the old inventory. The new inventory should:

1. Define provider values and semantic assertions in every sample, not only stratum labels.
2. Select only effective, historically tradable identity-session pairs for the ordinary stratum.
3. Include separately preregistered strata for actual first tradable session, delisting announcement and effective date, ST enter, ST exit, suspension, resumption, identity transition, and ordinary active status.
4. Use deterministic hash selection within exchange, year, board, and semantic strata, with counts fixed before observation.
5. Require official anchors for listing/delisting and identity transitions, and an independent daily source for market-observable ST/suspension/ordinary states.
6. Require zero unexplained semantic mismatches. Source unavailability may not count as MATCH. Any applicability exclusion must be decided from pre-observation identity/effective-interval rules.
7. Publish a semantic-specific coverage matrix. Dataset approval requires every research-used semantic to be either independently supported or conservatively unavailable until the next safe session.

No approval should be based only on a matched percentage. The replacement contract must test the missing semantics, not merely add more cases resembling the 30 existing matches.

## Research impact

Survivorship remains PASS because every confirmed historically tradable target A-share is covered by the original universe or immutable supplement. The evidence gap affects status equivalence and PIT knowledge time, not universe membership. Until a replacement contract is accepted and passes, `daily_security_status` stays PENDING, publication remains false, approved facts remain zero, and no DatasetManifest may be generated.
