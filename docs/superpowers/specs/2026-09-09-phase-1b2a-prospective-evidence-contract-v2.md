# V5.2 Phase 1B-2A Prospective Evidence Contract V2

Status: FROZEN BEFORE INDEPENDENT ACQUISITION.

V1 remains immutable and failed because its frozen ST_EXIT inventory treated risk-warning-name changes as exits. V2 is permitted only because the selector was corrected before this inventory was frozen. V1 is not superseded or reinterpreted.

Contract artifact: `ProspectiveEvidenceContractV2`.

Inventory artifact: `ProspectiveStatusSampleInventoryV2`.

Research scope is historically tradable target A-shares on SSE/SZSE from 2010-01-04 through 2025-12-31. The eight strata and fixed counts are active ordinary status 10, actual first tradable session 10, delisting boundary 10, ST enter 10, ST exit 10, full-day suspension 10, resumption 10, and identity transition 1.

Every sample must pin identity, session, semantic, provider value, semantic assertion, effective interval, provider evidence IDs, and a content-derived candidate hash. Its session must fall inside the effective interval and the identity must be confirmed historically tradable. ST_EXIT requires an effective transition from a risk-warning name to a non-risk-warning name; ST-to-*ST, *ST-to-ST, and other risk-warning-name transitions are not exits.

Selection is deterministic by canonical candidate hash and occurs before independent retrieval. Independent evidence may come from SSE, SZSE, exchange-hosted disclosures, or an independently operated daily source. DataHub endpoints remain provider-side evidence only.

Any unexplained semantic mismatch fails cross-source acceptance. Unavailable evidence remains unavailable and never becomes MATCH. PIT acceptance requires complete StatusAvailabilityPolicyV2 proof for every research-used semantic at the historical 16:30 Asia/Shanghai cutoff. Samples may not be replaced, removed, or reselected after results are observed.
