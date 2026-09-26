# V5.2 Phase 2B Private CAS Portability Design

## Purpose and authority

Checkpoint 18 needs a fresh checkout to replay the approved five-domain
2010-01 month without publishing restricted derived source bytes. The user
authorized a private content-addressed store and explicitly withheld public
redistribution authorization. This design changes only source transport; it
does not change Phase 1 approval, Phase 2A label semantics, or the current
historical cutoff.

## Exact boundary

The public repository contains code, already tracked approved artifacts, and
one `Phase2BPrivateCorpusManifestV1` of metadata. Only exact, currently
required and Git-untracked source files enter the private CAS: the frozen
Status authority/governance/shards, four approved CA files, two Calendar
extension/approval files, and the Master source-corpus inventory. Stale or
unrelated files in the same local directories do not enter the inventory.
The inventory builder first loads all five existing approved authorities and
then enumerates the files from their exact pins; it may not discover a
`latest` artifact or use a provider. Repository-relative logical paths are
transport roles, not authority identities or machine paths.

Each manifest entry records logical role, domain, exact-byte SHA-256, byte
size, media type, authority/approval/manifest IDs, optional coverage, and
`required_for_checkpoint18=true`. The manifest has a content hash over its
canonical bytes, canonical entry ordering, no duplicate logical roles, no
absolute/traversal paths, and no corpus bytes or credentials. A public guard
proves none of its object hashes is Git-tracked.

The CAS root defaults to `%LOCALAPPDATA%/V5_2/private-cas` and is overridden
only by `V5_2_PRIVATE_CAS_ROOT`. Objects live at
`sha256/<first-two-hex>/<full-sha256>`. Identity is SHA-256 of exact stored
bytes. Creation is exclusive; identical reacquisition is a no-op; a hash or
byte mismatch fails closed. Object files must be physical, not symlinks,
junctions, or hardlinks. Roots/paths are operational configuration only and
never enter research identities.

The resolver accepts the exact public manifest ID and explicit CAS root,
verifies every required object's path, type, size, SHA-256, and link status,
then materializes verified *copies* at those repository-relative roles in a
fresh checkout. The staged files are reread and rehashed before the existing
approved loaders consume them. Unset/incomplete CAS reports
`PRIVATE_CORPUS_UNAVAILABLE`; formal `CLEAN_ROOM_STANDALONE` remains FAIL.
There is no fallback to a main checkout, sibling worktree, junction,
provider, web, or latest directory. Unrelated extra CAS objects do not
participate in research truth.

## Acceptance

Fresh checkout + fresh environment + only manifest-pinned private CAS bytes
must reproduce the exact 2010-01 effective/materialized/pre-label/scoped
counts (34,271/26,899/6,950/422), partition ID, coverage evidence ID, and
row-comparison ledger ID. Missing, corrupted, replaced, linked, or
accidentally tracked private objects fail closed. Gate V2 and pilot
preregistration remain separate work; no Checkpoint 19 pilot is authorized.
