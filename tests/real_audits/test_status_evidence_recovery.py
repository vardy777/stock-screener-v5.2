from v5_2.data.real_audits.status_evidence_recovery import classify_recovery_failure


def test_recovery_failure_diagnosis_is_specific_and_fail_closed() -> None:
    assert classify_recovery_failure(http_status=None, tls_ok=False, json_ok=False, page_exists=False, semantic_mapped=False) == "TLS_OR_TRANSPORT"
    assert classify_recovery_failure(http_status=403, tls_ok=True, json_ok=False, page_exists=False, semantic_mapped=False) == "ACCESS_RESTRICTED"
    assert classify_recovery_failure(http_status=200, tls_ok=True, json_ok=False, page_exists=True, semantic_mapped=False) == "PARSE_FAILURE"
    assert classify_recovery_failure(http_status=200, tls_ok=True, json_ok=True, page_exists=False, semantic_mapped=False) == "PAGE_NOT_FOUND"
    assert classify_recovery_failure(http_status=200, tls_ok=True, json_ok=True, page_exists=True, semantic_mapped=False) == "SEMANTIC_MAPPING_FAILURE"
    assert classify_recovery_failure(http_status=200, tls_ok=True, json_ok=True, page_exists=True, semantic_mapped=True) == "RECOVERED"
