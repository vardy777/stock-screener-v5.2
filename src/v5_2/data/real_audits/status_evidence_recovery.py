from __future__ import annotations


def classify_recovery_failure(*, http_status: int | None, tls_ok: bool, json_ok: bool,
                              page_exists: bool, semantic_mapped: bool) -> str:
    if not tls_ok or http_status is None:
        return "TLS_OR_TRANSPORT"
    if http_status in {401, 403, 429}:
        return "ACCESS_RESTRICTED"
    if http_status >= 400:
        return "HTTP_OR_PARAMETER_FAILURE"
    if not json_ok:
        return "PARSE_FAILURE"
    if not page_exists:
        return "PAGE_NOT_FOUND"
    if not semantic_mapped:
        return "SEMANTIC_MAPPING_FAILURE"
    return "RECOVERED"
