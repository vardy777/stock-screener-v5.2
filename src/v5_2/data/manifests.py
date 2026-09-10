from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from v5_2.data.identity import content_hash
from v5_2.data.source_approval import ApprovalDecision, SourceApprovalArtifactV1


class ManifestError(RuntimeError):
    """An approved immutable dataset manifest cannot be constructed."""


@dataclass(frozen=True, slots=True)
class DatasetManifestV1:
    dataset_id: str
    created_at: datetime
    source_name: str
    dataset_kind: str
    approval_id: str
    approval_content_hash: str
    approval_resolution_as_of: datetime
    coverage_start: date
    coverage_end: date
    row_count: int
    symbol_count: int
    raw_payload_hashes: tuple[str, ...]
    normalized_content_hashes: tuple[str, ...]
    fact_content_hashes: tuple[str, ...]
    normalizer_version: str
    availability_policy_version: str
    quality_findings: tuple[str, ...]
    pit_validation_status: str
    rule_compliance_status: str
    pagination_complete: bool
    equivalence_evidence_id: str | None
    audit_policy_id: str | None
    endpoint_identities: tuple[str, ...]
    receipt_hashes: tuple[str, ...]
    input_count: int | None
    eligible_count: int | None
    excluded_non_target_count: int | None
    quarantined_count: int | None
    quarantined_identity_hashes: tuple[str, ...]
    approval_policy_id: str | None
    upstream_approval_ids: tuple[str, ...]
    request_inventory_id: str | None
    normalization_policy_id: str | None
    unit_policy_id: str | None
    exception_policy_id: str | None
    exception_set_hash: str | None
    cross_source_evidence_id: str | None
    availability_evidence_id: str | None
    supported_action_types: tuple[str, ...]
    unsupported_action_types: tuple[str, ...]
    validated_coverage_by_action_type: tuple[tuple[str, date, date], ...]
    materialized_coverage_by_action_type: tuple[tuple[str, date, date], ...]
    coverage_gaps: tuple[tuple[date, date, str], ...]
    unsupported_intervals: tuple[tuple[str, date, date], ...]
    latest_approved_session: date | None
    manifest_hash: str

    @classmethod
    def create(
        cls,
        *,
        created_at: datetime,
        source_name: str,
        dataset_kind: str,
        approval: SourceApprovalArtifactV1,
        approval_resolution_as_of: datetime,
        coverage_start: date,
        coverage_end: date,
        row_count: int,
        symbol_count: int,
        raw_payload_hashes: tuple[str, ...],
        normalized_content_hashes: tuple[str, ...],
        fact_content_hashes: tuple[str, ...],
        normalizer_version: str,
        availability_policy_version: str,
        quality_findings: tuple[str, ...],
        pit_validation_status: str,
        rule_compliance_status: str,
        pagination_complete: bool,
        audit_policy_id: str | None = None,
        endpoint_identities: tuple[str, ...] = (),
        receipt_hashes: tuple[str, ...] = (),
        input_count: int | None = None,
        eligible_count: int | None = None,
        excluded_non_target_count: int | None = None,
        quarantined_count: int | None = None,
        quarantined_identity_hashes: tuple[str, ...] = (),
        approval_policy_id: str | None = None,
        upstream_approval_ids: tuple[str, ...] = (),
        request_inventory_id: str | None = None,
        normalization_policy_id: str | None = None,
        unit_policy_id: str | None = None,
        exception_policy_id: str | None = None,
        exception_set_hash: str | None = None,
        cross_source_evidence_id: str | None = None,
        availability_evidence_id: str | None = None,
        supported_action_types: tuple[str, ...] = (),
        unsupported_action_types: tuple[str, ...] = (),
        validated_coverage_by_action_type: tuple[tuple[str, date, date], ...] = (),
        materialized_coverage_by_action_type: tuple[tuple[str, date, date], ...] = (),
        coverage_gaps: tuple[tuple[date, date, str], ...] = (),
        unsupported_intervals: tuple[tuple[str, date, date], ...] = (),
        latest_approved_session: date | None = None,
    ) -> DatasetManifestV1:
        approving = {ApprovalDecision.APPROVED, ApprovalDecision.APPROVED_WITH_RULES}
        if approval.decision not in approving:
            raise ManifestError("manifest requires an approving artifact")
        if approval.source_name != source_name or approval.dataset_kind != dataset_kind:
            raise ManifestError("approval scope does not match dataset")
        if coverage_end < coverage_start or not (
            approval.coverage_start <= coverage_start
            and approval.coverage_end >= coverage_end
        ):
            raise ManifestError("dataset coverage is not contained by approval")
        if pit_validation_status != "PASS":
            raise ManifestError("PIT validation must PASS")
        if rule_compliance_status != "PASS":
            raise ManifestError("approval rule compliance must PASS")
        if pagination_complete is not True:
            raise ManifestError("pagination must be complete")
        if row_count < 0 or symbol_count < 0 or symbol_count > row_count:
            raise ManifestError("dataset counts are invalid")
        if not raw_payload_hashes or not normalized_content_hashes or not fact_content_hashes:
            raise ManifestError("dataset lineage hashes must not be empty")
        if source_name == "datahubco_tushare_proxy" and (
            not approval.equivalence_evidence_id
            or not audit_policy_id
            or not endpoint_identities
            or not receipt_hashes
            or not approval_policy_id
        ):
            raise ManifestError("DataHub manifest requires extended lineage")
        if source_name == "datahubco_tushare_proxy" and dataset_kind == "security_master":
            counts = (input_count, eligible_count, excluded_non_target_count, quarantined_count)
            if any(value is None or value < 0 for value in counts):
                raise ManifestError("security master disposition counts are invalid")
            assert all(value is not None for value in counts)
            if eligible_count + excluded_non_target_count + quarantined_count != input_count:
                raise ManifestError("security master disposition counts do not reconcile")
            if eligible_count != row_count or len(quarantined_identity_hashes) != quarantined_count:
                raise ManifestError("security master quarantine lineage is incomplete")
        if source_name == "datahubco_tushare_proxy" and dataset_kind == "daily_bar" and (
            len(upstream_approval_ids) != 2
            or not request_inventory_id
            or not normalization_policy_id
            or not unit_policy_id
            or not exception_policy_id
            or not exception_set_hash
            or not cross_source_evidence_id
            or not availability_evidence_id
        ):
            raise ManifestError("daily bar manifest requires frozen governance and audit lineage")
        if source_name == "datahubco_tushare_proxy" and dataset_kind == "corporate_action" and (
            not supported_action_types or not unsupported_action_types
            or not validated_coverage_by_action_type or not materialized_coverage_by_action_type
            or not unsupported_intervals or latest_approved_session is None
            or not availability_evidence_id
        ):
            raise ManifestError("corporate action manifest requires scoped coverage lineage")
        for name, value in (
            ("created_at", created_at),
            ("approval_resolution_as_of", approval_resolution_as_of),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ManifestError(f"{name} must be timezone-aware")
        body = {
            "schema_version": "DatasetManifestV1",
            "created_at": created_at,
            "source_name": source_name,
            "dataset_kind": dataset_kind,
            "approval_id": approval.approval_id,
            "approval_content_hash": approval.content_hash,
            "approval_resolution_as_of": approval_resolution_as_of,
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "row_count": row_count,
            "symbol_count": symbol_count,
            "raw_payload_hashes": raw_payload_hashes,
            "normalized_content_hashes": normalized_content_hashes,
            "fact_content_hashes": fact_content_hashes,
            "normalizer_version": normalizer_version,
            "availability_policy_version": availability_policy_version,
            "quality_findings": tuple(sorted(quality_findings)),
            "pit_validation_status": pit_validation_status,
            "rule_compliance_status": rule_compliance_status,
            "pagination_complete": pagination_complete,
            "equivalence_evidence_id": approval.equivalence_evidence_id,
            "audit_policy_id": audit_policy_id,
            "endpoint_identities": tuple(sorted(set(endpoint_identities))),
            "receipt_hashes": tuple(sorted(set(receipt_hashes))),
            "input_count": input_count,
            "eligible_count": eligible_count,
            "excluded_non_target_count": excluded_non_target_count,
            "quarantined_count": quarantined_count,
            "quarantined_identity_hashes": tuple(sorted(set(quarantined_identity_hashes))),
            "approval_policy_id": approval_policy_id,
            "upstream_approval_ids": tuple(upstream_approval_ids),
            "request_inventory_id": request_inventory_id,
            "normalization_policy_id": normalization_policy_id,
            "unit_policy_id": unit_policy_id,
            "exception_policy_id": exception_policy_id,
            "exception_set_hash": exception_set_hash,
            "cross_source_evidence_id": cross_source_evidence_id,
            "availability_evidence_id": availability_evidence_id,
            "supported_action_types": tuple(sorted(set(supported_action_types))),
            "unsupported_action_types": tuple(sorted(set(unsupported_action_types))),
            "validated_coverage_by_action_type": tuple(sorted(validated_coverage_by_action_type)),
            "materialized_coverage_by_action_type": tuple(sorted(materialized_coverage_by_action_type)),
            "coverage_gaps": tuple(sorted(coverage_gaps)),
            "unsupported_intervals": tuple(sorted(unsupported_intervals)),
            "latest_approved_session": latest_approved_session,
        }
        digest = content_hash(body)
        values = dict(body)
        values.pop("schema_version")
        return cls(dataset_id=digest, manifest_hash=digest, **values)  # type: ignore[arg-type]

    def verify_pinned_approval(self, approval: SourceApprovalArtifactV1) -> bool:
        return (
            approval.approval_id == self.approval_id
            and approval.content_hash == self.approval_content_hash
            and approval.approval_id == approval.content_hash
        )
