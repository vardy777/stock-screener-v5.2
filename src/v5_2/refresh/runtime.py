from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from v5_2.data.identity import canonical_json, content_hash
from v5_2.data.acquisition import AcquisitionControls, acquire_pages
from v5_2.data.checkpoints import CheckpointStore
from v5_2.data.raw_artifacts import RawPayloadArtifactV1
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.integrations.datahub_http import DataHubHttpTransport
from v5_2.providers.credentials import load_datahub_credential
from v5_2.providers.credentials import Credential
from v5_2.providers.datahub import DataHubClient
from v5_2.providers.rate_limit import RateLimiter
from v5_2.providers.retry import RetryPolicyV1
from v5_2.refresh.adapters import AvailabilityMode, DatasetStateV1, SHANGHAI
from v5_2.refresh.contracts import DatasetReadiness, DatasetRefreshResultV1, SnapshotStore
from v5_2.refresh.calendar import publish_calendar_increment
from v5_2.refresh.security_master import publish_security_master_increment
from v5_2.refresh.daily_bar import daily_bar_state_at, publish_daily_bar_increment
from v5_2.refresh.security_status import publish_security_status_increment, security_status_state_at
from v5_2.refresh.corporate_action import publish_corporate_action_increment
from v5_2.refresh.financial_disclosure import publish_financial_scope_assessment
from v5_2.refresh.planning import ApprovedCalendarView
from v5_2.refresh.service import RefreshService
from v5_2.providers.contracts import ProviderRequestV1


BASELINE = {
    "trade_calendar": (
        "4a900c7e4f2b171d7adac07088025ca4bb9fb0da13cfa1b15e91eff3dafea601",
        "5f5ba7d0594f5f1e2d40ad43b54a93a303a7d25af8e1104e6c633463076e6486",
        date(2026, 9, 11), DatasetReadiness.READY,
    ),
    "security_master": (
        "828e0e722d3d66c84a48584aac14fde37f86cf471f3722f403ec19044f36345c",
        "025982975b942c416945d9580f2a8272d667f7676e9f6fa213429e3da2ee382b",
        date(2026, 9, 10), DatasetReadiness.READY,
    ),
    "daily_bar": (
        "fc26bf140708a72957f687757665508ee439cb079b9bdaff86686109b7683ea5",
        "76c4fe58d0714405d0a6a826bf9b814237d812f88f69b63986a0e0317f924b4b",
        date(2026, 9, 10), DatasetReadiness.READY,
    ),
    "daily_security_status": (
        "ac1c23dae38c32228bfc6639714976e6a01063b230ae3397ee45d9ac1d8afa07",
        "d96fc4f26c459dc000ca8059a8364a8236e906305be83d2d72adc01d9e11ffb0",
        date(2026, 9, 10), DatasetReadiness.READY,
    ),
    "corporate_action": (
        "5e53080fd85dba5328cda9ed44c5dc5959e5bea965d8f5df12e07201deb8e974",
        "5086896d0066baa928fe44c3469b2c1362feb2068db04acb7336b38c13bdbe2c",
        date(2026, 9, 10), DatasetReadiness.SCOPED_READY,
    ),
    "financial_disclosure": (
        "58afcda2811226574060a352351eb00fc09b066a43c512c1843a8821f69f0498",
        "0b5e72283c045c485eff9ecd2161f019980bdea7ccb33fbcdbdf137d1e13706f",
        date(2026, 9, 10), DatasetReadiness.SCOPED_READY,
    ),
}


def resolve_governance_artifact(runtime_governance: Path, baseline_governance: Path,
                                filename: str) -> Path:
    current = runtime_governance / filename
    if current.is_file():
        return current
    baseline = baseline_governance / filename
    if baseline.is_file():
        return baseline
    raise FileNotFoundError(filename)


def resolve_endpoint_capability(evidence_ids: tuple[str, ...],
                                governance_roots: tuple[Path, ...]) -> Path:
    for evidence_id in evidence_ids:
        for root in governance_roots:
            path = root / f"endpoint-capability-{evidence_id}.json"
            if not path.is_file():
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            body = {key: item for key, item in value.items()
                    if key not in {"audit_id", "content_hash"}}
            if (value.get("schema_version") == "FinancialEndpointCapabilityAuditV1"
                    and value.get("audit_id") == evidence_id
                    and value.get("content_hash") == evidence_id
                    and content_hash(body) == evidence_id):
                return path
    raise FileNotFoundError("approved financial endpoint capability evidence")


class IncrementalValidationRequired(RuntimeError):
    """Raw acquisition completed, but no approved facts may be inferred from it."""

    def __init__(self, artifact_id: str) -> None:
        super().__init__("incremental acquisition requires dataset validation")
        self.artifact_id = artifact_id


class RawIncrementalExecutor:
    """Persist an immutable acquisition candidate without self-approving it.

    Dataset-specific validators/publishers consume this candidate in later wiring.
    Until then, raising after persistence preserves the previous ready snapshot.
    """

    def __init__(self, root: Path, *,
                 acquire: Callable[[ProviderRequestV1], tuple[RawPayloadArtifactV1, ...]],
                 clock: Callable[[], datetime],
                 publisher: Callable[[str, DatasetStateV1, date, tuple[date, ...],
                                      tuple[RawPayloadArtifactV1, ...], datetime], DatasetStateV1]
                 | None = None) -> None:
        self._root = root
        self._acquire = acquire
        self._clock = clock
        self._publisher = publisher

    def __call__(self, dataset_kind: str, current: DatasetStateV1,
                 target_session: date,
                 missing_sessions: tuple[date, ...]) -> DatasetStateV1:
        if dataset_kind == "financial_disclosure" and self._publisher is not None:
            return self._publisher(dataset_kind, current, target_session,
                                   missing_sessions, (), self._clock())
        requests = build_incremental_requests(dataset_kind, missing_sessions)
        artifacts = tuple(
            artifact for request in requests for artifact in self._acquire(request)
        )
        observed_at = self._clock()
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("incremental acquisition clock must be timezone-aware")
        body = {
            "schema_version": "Phase1CIncrementalCandidateV1",
            "dataset_kind": dataset_kind,
            "target_session": target_session,
            "missing_sessions": tuple(missing_sessions),
            "prior_approval_id": current.approval_id,
            "prior_manifest_id": current.manifest_id,
            "request_ids": tuple(request.request_id for request in requests),
            "payload_hashes": tuple(artifact.payload_hash for artifact in artifacts),
            "row_count": sum(len(artifact.provider_payload["rows"]) for artifact in artifacts),
            "observed_at": observed_at,
            "validation_status": "PENDING",
            "publication_allowed": False,
        }
        artifact_id = content_hash(body)
        encoded = canonical_json({"artifact_id": artifact_id, **body})
        path = self._root / "governance" / "incremental-candidates" / f"{artifact_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            if path.read_bytes() != encoded:
                raise RuntimeError("immutable incremental candidate collision") from None
        else:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
        if self._publisher is not None:
            return self._publisher(dataset_kind, current, target_session,
                                   missing_sessions, artifacts, observed_at)
        raise IncrementalValidationRequired(artifact_id)


def build_raw_incremental_executor(root: Path, *,
                                   clock: Callable[[], datetime] | None = None
                                   ) -> RawIncrementalExecutor:
    """Build the credential-safe production acquisition boundary lazily.

    Constructing and running a no-op refresh does not read credentials. The
    first real request loads the local ignored credential and reuses the
    established pagination, retry, rate-limit, receipt and checkpoint code.
    """
    runtime_root = root / "data" / "phase_1c"
    raw_store = RawArtifactStore(runtime_root)
    checkpoints = CheckpointStore(runtime_root)
    client = DataHubClient(transport=DataHubHttpTransport(timeout_seconds=30))
    controls = AcquisitionControls(
        retry_policy=RetryPolicyV1(3, 1.0, 4.0, "phase-1c-datahub-retry-v1"),
        rate_limiter=RateLimiter(min_interval_seconds=.25),
        monotonic_clock=time.monotonic, sleeper=time.sleep,
        utc_clock=clock or (lambda: datetime.now().astimezone()),
    )
    credential_box: list[Credential] = []

    def acquire(request: ProviderRequestV1) -> tuple[RawPayloadArtifactV1, ...]:
        if not credential_box:
            credential_box.append(load_datahub_credential(
                env={}, env_file=root / ".env", repository_root=root,
            ))
        return acquire_pages(
            request=request, client=client, credential=credential_box[0],
            raw_store=raw_store, checkpoint_store=checkpoints,
            acquisition_policy_version="phase-1c-datahub-acquisition-v1",
            controls=controls, resume=checkpoints.exists(request.request_id),
        )

    def publish(kind: str, current: DatasetStateV1, target: date,
                missing: tuple[date, ...], artifacts: tuple[RawPayloadArtifactV1, ...],
                observed_at: datetime) -> DatasetStateV1:
        receipt_hashes: list[str] = []
        for artifact in artifacts:
            receipt_paths = tuple((runtime_root / "receipts" / artifact.payload_hash[:16]).glob("*.json"))
            if not receipt_paths:
                raise IncrementalValidationRequired(content_hash((kind, target, "MISSING_RECEIPT")))
            receipts = [raw_store.read_receipt(path) for path in receipt_paths]
            receipt_hashes.append(min(receipts, key=lambda item: item.acquired_at).receipt_hash)
        if kind == "security_master":
            approval_path = resolve_governance_artifact(runtime_root/'governance',
                root/'data/phase_1b1_2026_extension/governance',f"security_master-approval-{current.approval_id}.json")
            runtime_manifest=runtime_root/'governance'/f"security_master-manifest-{current.manifest_id}.json"
            manifest_path=(runtime_manifest if runtime_manifest.is_file() else
                root / "data/phase_1b_exit_remediation/governance" / f"security-master-complete-manifest-{current.manifest_id}.json")
            universe_path = root / "data/phase_1b1_2026_extension/governance/universe-extension-016d9b64bb0cda79583a06eb2cc1c89c7b8668e3d63a354b44a159668dd8975f.json"
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            universe = json.loads(universe_path.read_text(encoding="utf-8"))
            prior = set(universe["baseline_symbols"])
            for symbol, listing, delisting, _ in universe["changes"]:
                if listing <= current.latest_approved_session.isoformat() and (delisting is None or delisting >= current.latest_approved_session.isoformat()): prior.add(symbol)
                elif delisting is not None and delisting < current.latest_approved_session.isoformat(): prior.discard(symbol)
            calendar_sessions = _load_published_state(runtime_root, "trade_calendar", current).completed_sessions
            return publish_security_master_increment(output_root=runtime_root,
                previous_approval=approval, previous_manifest=manifest, raws=artifacts,
                receipt_hashes=tuple(receipt_hashes), prior_effective_symbols=frozenset(prior),
                target_session=target, approved_open_sessions=calendar_sessions,
                observed_at=observed_at).state
        if kind == "daily_bar":
            approval_path=resolve_governance_artifact(runtime_root/'governance',root/'data/phase_1b_exit_remediation/governance',f'daily_bar-approval-{current.approval_id}.json')
            manifest_path=resolve_governance_artifact(runtime_root/'governance',root/'data/phase_1b_exit_remediation/governance',f'daily_bar-manifest-{current.manifest_id}.json')
            approval=json.loads(approval_path.read_text(encoding='utf-8'))
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            eligible_paths=tuple((runtime_root/'governance').glob('eligible-universe-*.json'))
            candidates=[json.loads(path.read_text(encoding='utf-8')) for path in eligible_paths]
            eligible=next(item for item in candidates if item.get('target_session')==target.isoformat())
            calendar_state=_load_published_state(runtime_root,'trade_calendar',current)
            next_session=min((day for day in calendar_state.completed_sessions if day>target),default=target)
            return publish_daily_bar_increment(output_root=runtime_root,previous_approval=approval,
                previous_manifest=manifest,raws=artifacts,receipt_hashes=tuple(receipt_hashes),
                research_safe_symbols=tuple(eligible['symbols']),session=target,next_approved_session=next_session,
                observed_at=observed_at,prior_completed_sessions=current.completed_sessions).state
        if kind == "daily_security_status":
            approval_path = root/'data/phase_1b_exit_remediation/governance'/f'daily_security_status-approval-{current.approval_id}.json'
            manifest_path = root/'data/phase_1b_exit_remediation/governance'/f'daily_security_status-manifest-{current.manifest_id}.json'
            if not approval_path.is_file(): approval_path = runtime_root/'governance'/f'daily_security_status-approval-{current.approval_id}.json'
            if not manifest_path.is_file(): manifest_path = runtime_root/'governance'/f'daily_security_status-manifest-{current.manifest_id}.json'
            approval=json.loads(approval_path.read_text(encoding='utf-8'))
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            panel_id=str(approval['rule_set']['panel_id'])
            panel=json.loads((root/'data/phase_1b_exit_remediation/governance'/f'historical-status-panel-{panel_id}.json').read_text(encoding='utf-8'))
            prior_risk_rows={}
            for historical_root in (root/'data/phase_1b2a',root/'data/phase_1b_exit_status_2026'):
                for path in (historical_root/'raw/datahubco_tushare_proxy/risk_warning_history').rglob('*.json'):
                    value=json.loads(path.read_text(encoding='utf-8'))
                    for row in value['provider_payload']['rows']:
                        prior_risk_rows[content_hash(row)]=row
            master_state=_load_published_state(runtime_root,'security_master',current)
            eligible=[json.loads(path.read_text(encoding='utf-8')) for path in (runtime_root/'governance').glob('eligible-universe-*.json')]
            universe=next(item for item in eligible if item.get('target_session')==target.isoformat())
            calendar_state=_load_published_state(runtime_root,'trade_calendar',current)
            next_session=min((day for day in calendar_state.completed_sessions if day>target),default=target)
            return publish_security_status_increment(output_root=runtime_root,previous_approval=approval,
                previous_manifest=manifest,previous_panel=panel,prior_risk_warning_rows=tuple(prior_risk_rows.values()),
                raws=artifacts,receipt_hashes=tuple(receipt_hashes),
                research_safe_symbols=tuple(universe['symbols']),upstream_master_approval_id=master_state.approval_id,
                upstream_master_manifest_id=master_state.manifest_id,target_session=target,next_approved_session=next_session,
                observed_at=observed_at,prior_completed_sessions=current.completed_sessions).state
        if kind == "corporate_action":
            approval_path=root/'data/phase_1b2c/governance'/f'corporate_action-approval-{current.approval_id}.json'
            manifest_path=root/'data/phase_1b2c/governance'/f'corporate-action-manifest-{current.manifest_id}.json'
            if not approval_path.is_file(): approval_path=runtime_root/'governance'/f'corporate_action-approval-{current.approval_id}.json'
            if not manifest_path.is_file(): manifest_path=runtime_root/'governance'/f'corporate_action-manifest-{current.manifest_id}.json'
            return publish_corporate_action_increment(output_root=runtime_root,
                previous_approval=json.loads(approval_path.read_text(encoding='utf-8')),
                previous_manifest=json.loads(manifest_path.read_text(encoding='utf-8')),raws=artifacts,
                receipt_hashes=tuple(receipt_hashes),target_session=target,observed_at=observed_at,
                prior_completed_sessions=current.completed_sessions).state
        if kind == "financial_disclosure":
            approval_path=root/'data/phase_1b2d/governance'/f'financial-disclosure-approval-{current.approval_id}.json'
            manifest_path=root/'data/phase_1b2d/governance'/f'financial-disclosure-manifest-{current.manifest_id}.json'
            if not approval_path.is_file(): approval_path=runtime_root/'governance'/f'financial_disclosure-approval-{current.approval_id}.json'
            if not manifest_path.is_file(): manifest_path=runtime_root/'governance'/f'financial_disclosure-manifest-{current.manifest_id}.json'
            approval=json.loads(approval_path.read_text(encoding='utf-8'))
            capability_path=resolve_endpoint_capability(tuple(approval['evidence_ids']),(
                root/'data/phase_1b2d/governance',runtime_root/'governance'))
            return publish_financial_scope_assessment(output_root=runtime_root,
                previous_approval=approval,
                previous_manifest=json.loads(manifest_path.read_text(encoding='utf-8')),
                endpoint_capability=json.loads(capability_path.read_text(encoding='utf-8')),
                target_session=target,observed_at=observed_at,prior_completed_sessions=current.completed_sessions).state
        if kind != "trade_calendar":
            raise IncrementalValidationRequired(content_hash((kind, target, tuple(a.payload_hash for a in artifacts))))
        approval_path = root / "data/phase_1b1_2026_extension/governance" / (
            f"trade_calendar-approval-{current.approval_id}.json"
        )
        manifest_path = root / "data/phase_1b_exit_remediation/governance" / (
            f"trade-calendar-complete-manifest-{current.manifest_id}.json"
        )
        if not approval_path.is_file():
            approval_path = runtime_root / "governance" / f"trade_calendar-approval-{current.approval_id}.json"
        if not manifest_path.is_file():
            manifest_path = runtime_root / "governance" / f"trade_calendar-manifest-{current.manifest_id}.json"
        previous_approval = json.loads(approval_path.read_text(encoding="utf-8"))
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return publish_calendar_increment(
            output_root=runtime_root, previous_approval=previous_approval,
            previous_manifest=previous_manifest, raws=artifacts,
            receipt_hashes=tuple(receipt_hashes), missing_dates=missing,
            observed_at=observed_at, prior_open_sessions=current.completed_sessions,
        ).state

    return RawIncrementalExecutor(
        runtime_root, acquire=acquire,
        clock=clock or (lambda: datetime.now().astimezone()), publisher=publish,
    )


def _request(kind: str, endpoint: str, parameters: dict[str, object],
             fields: tuple[str, ...]) -> ProviderRequestV1:
    parameters = {**parameters, "fields": ",".join(fields)}
    return ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind=kind, endpoint=endpoint,
        parameters=parameters, requested_fields=fields, page_size=5000,
        request_policy_version="phase-1c-incremental-v1",
    )


def build_incremental_requests(dataset_kind: str,
                               missing_sessions: tuple[date, ...]) -> tuple[ProviderRequestV1, ...]:
    if not missing_sessions:
        return ()
    ordered = tuple(sorted(set(missing_sessions)))
    start, end = ordered[0].strftime("%Y%m%d"), ordered[-1].strftime("%Y%m%d")
    if dataset_kind == "trade_calendar":
        fields = ("exchange", "cal_date", "is_open", "pretrade_date")
        return tuple(_request("trade_calendar", "trade-cal", {
            "exchange": exchange, "start_date": start, "end_date": end}, fields)
            for exchange in ("SSE", "SZSE"))
    if dataset_kind == "security_master":
        fields = ("ts_code", "symbol", "name", "market", "exchange", "list_status", "list_date", "delist_date")
        return tuple(_request("security_master", "stock-basic", {
            "exchange": exchange, "list_status": status}, fields)
            for exchange in ("SSE", "SZSE") for status in ("L", "D", "P"))
    if dataset_kind == "daily_bar":
        fields = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")
        return tuple(_request("daily_bar", "daily", {"trade_date": day.strftime("%Y%m%d")}, fields)
                     for day in ordered)
    if dataset_kind == "daily_security_status":
        name = ("ts_code", "name", "start_date", "end_date", "ann_date", "change_reason")
        suspend = ("ts_code", "trade_date", "suspend_timing", "suspend_type")
        return (_request("risk_warning_history", "namechange", {"start_date": start, "end_date": end}, name),
                _request("suspension_history", "suspend-d", {"start_date": start, "end_date": end}, suspend))
    if dataset_kind == "corporate_action":
        fields = ("ts_code", "ann_date", "div_proc", "stk_div", "cash_div_tax", "record_date", "ex_date", "pay_date")
        return (_request("corporate_action", "dividend", {"start_date": start, "end_date": end}, fields),)
    if dataset_kind == "financial_disclosure":
        specs = {
            "financial_income": ("income", ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "update_flag", "total_revenue", "revenue", "n_income", "n_income_attr_p")),
            "financial_balance_sheet": ("balancesheet", ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "update_flag", "total_assets", "total_liab", "total_hldr_eqy_exc_min_int")),
            "financial_cash_flow": ("cashflow", ("ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "update_flag", "n_cashflow_act", "n_cashflow_inv_act", "n_cash_flows_fnc_act")),
        }
        return tuple(_request(kind, endpoint, {"start_date": start, "end_date": end}, fields)
                     for kind, (endpoint, fields) in specs.items())
    raise ValueError("unknown refresh dataset kind")


def classify_refresh_availability(session: date, observed_at: datetime):
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    local_day = observed_at.astimezone(SHANGHAI).date()
    mode = (AvailabilityMode.CONTEMPORANEOUS_OBSERVED
            if session == local_day else AvailabilityMode.HISTORICAL_RECONSTRUCTED)
    return mode, observed_at


def _approved_open_sessions(root: Path) -> tuple[date, ...]:
    by_exchange: dict[tuple[str, str], int] = {}
    for runtime in (root / "data/phase_1b1", root / "data/phase_1b1_2026_extension"):
        raw = runtime / "raw/datahubco_tushare_proxy/trade_calendar"
        for path in raw.rglob("*.json") if raw.is_dir() else ():
            value = json.loads(path.read_text(encoding="utf-8"))
            for row in value["provider_payload"]["rows"]:
                by_exchange[(str(row["exchange"]), str(row["cal_date"]))] = int(row["is_open"])
    sessions = {
        day for (_, day), is_open in by_exchange.items() if is_open == 1
    }
    if not sessions:
        raise RuntimeError("approved calendar facts are unavailable")
    return tuple(date(int(day[:4]), int(day[4:6]), int(day[6:])) for day in sorted(sessions))


def _load_published_state(state_root: Path, kind: str,
                          fallback: DatasetStateV1) -> DatasetStateV1:
    pointer = state_root / f"{kind}-current-state-id.txt"
    if not pointer.is_file():
        state = fallback
    else:
        state_id = pointer.read_text(encoding="ascii").strip()
        path = state_root / "governance" / f"{kind}-state-{state_id}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        claimed = value.pop("state_id", None)
        if claimed != state_id or content_hash(value) != state_id:
            raise RuntimeError("published refresh state integrity invalid")
        value.pop("schema_version", None)
        value["latest_approved_session"] = date.fromisoformat(value["latest_approved_session"])
        value["completed_sessions"] = tuple(date.fromisoformat(item) for item in value["completed_sessions"])
        value["readiness"] = DatasetReadiness(value["readiness"])
        for name in ("reason_codes", "affected_security_ids", "availability_modes"):
            value[name] = tuple(value[name])
        state = DatasetStateV1(**value)
    remediation = state_root.parent / "phase_1c_lineage_remediation"
    if kind == "daily_bar" and (remediation / "daily_bar-current-composite-id.txt").is_file():
        from dataclasses import replace
        from v5_2.refresh.daily_bar_composite import resolve_phase1c_daily_bar_composite
        state = replace(state, approval_id=None,
                        manifest_id=resolve_phase1c_daily_bar_composite(remediation),
                        availability_modes=("HISTORICAL_RECONSTRUCTED", "CONTEMPORANEOUS_OBSERVED"))
    return state


IncrementalExecutor = Callable[
    [str, DatasetStateV1, date, tuple[date, ...]], DatasetStateV1
]


class _PinnedAdapter:
    def __init__(self, state_root: Path, kind: str, sessions: tuple[date, ...],
                 executor: IncrementalExecutor | None = None,
                 clock: Callable[[],datetime] | None = None) -> None:
        self.dataset_kind = kind
        self.required = kind in {"trade_calendar", "security_master", "daily_bar", "daily_security_status"}
        approval, manifest, through, readiness = BASELINE[kind]
        completed = tuple(item for item in sessions if item <= through)
        modes = (AvailabilityMode.HISTORICAL_RECONSTRUCTED.value,)
        fallback = DatasetStateV1(kind, approval, manifest, through, completed,
                                  through.isoformat(), readiness=readiness,
                                  availability_modes=modes)
        self._state = _load_published_state(state_root, kind, fallback)
        self._executor = executor
        self._clock = clock or (lambda: datetime.now().astimezone())

    def inspect_current_state(self) -> DatasetStateV1:
        return self._state

    def refresh(self, target_session: date,
                missing_sessions: tuple[date, ...]) -> DatasetRefreshResultV1:
        if (self.dataset_kind == 'daily_bar' and not missing_sessions
                and self._state.reason_codes == ('AVAILABILITY_NOT_REACHED',)
                and self._state.watermark.startswith('visibility:')):
            visible=daily_bar_state_at(self._state,self._clock())
            if visible.readiness is DatasetReadiness.READY:
                return DatasetRefreshResultV1(visible.dataset_kind,visible.readiness,visible.approval_id,
                    visible.manifest_id,visible.latest_approved_session,visible.availability_modes,
                    visible.reason_codes,visible.affected_security_ids)
        if (self.dataset_kind == 'daily_security_status' and not missing_sessions
                and self._state.reason_codes == ('AVAILABILITY_NOT_REACHED',)):
            visible=security_status_state_at(self._state,self._clock())
            if visible.readiness is DatasetReadiness.READY:
                return DatasetRefreshResultV1(visible.dataset_kind,visible.readiness,visible.approval_id,
                    visible.manifest_id,visible.latest_approved_session,visible.availability_modes,
                    visible.reason_codes,visible.affected_security_ids)
        if missing_sessions or self._state.latest_approved_session < target_session:
            if self._executor is None:
                raise RuntimeError("incremental provider execution is required")
            previous = self._state
            published = self._executor(
                self.dataset_kind, previous, target_session, tuple(missing_sessions)
            )
            if published.dataset_kind != self.dataset_kind:
                raise ValueError("incremental executor returned the wrong dataset")
            self._state = published
            return DatasetRefreshResultV1(
                self.dataset_kind, published.readiness, published.approval_id,
                published.manifest_id, published.latest_approved_session,
                published.availability_modes, published.reason_codes,
                published.affected_security_ids,
                changed=published.manifest_id != previous.manifest_id,
            )
        return DatasetRefreshResultV1(
            self.dataset_kind, self._state.readiness, self._state.approval_id,
            self._state.manifest_id, self._state.latest_approved_session,
            self._state.availability_modes, self._state.reason_codes,
            self._state.affected_security_ids,
        )


class _PinnedCalendarAdapter(_PinnedAdapter):
    def __init__(self, root: Path, sessions: tuple[date, ...],
                 executor: IncrementalExecutor | None = None) -> None:
        super().__init__(root, "trade_calendar", sessions, executor)
        self._sessions = self._state.completed_sessions

    def ensure_calendar_through(self, today: date) -> None:
        if today > self._state.latest_approved_session:
            if self._executor is None:
                raise RuntimeError("calendar increment is required")
            start = self._state.latest_approved_session.fromordinal(
                self._state.latest_approved_session.toordinal() + 1
            )
            civil_dates = tuple(
                date.fromordinal(day)
                for day in range(start.toordinal(), today.toordinal() + 1)
            )
            published = self._executor("trade_calendar", self._state, today, civil_dates)
            if published.dataset_kind != "trade_calendar":
                raise ValueError("calendar executor returned the wrong dataset")
            self._state = published
            self._sessions = published.completed_sessions

    def calendar_view(self) -> ApprovedCalendarView:
        return ApprovedCalendarView(
            self._state.manifest_id, date(2010, 1, 1),
            self._state.latest_approved_session, self._sessions,
        )


def build_refresh_service(root: Path, *, snapshot_root: Path | None = None,
                          clock: Callable[[], datetime] | None = None,
                          incremental_executor: IncrementalExecutor | None = None,
                          published_state_root: Path | None = None) -> RefreshService:
    sessions = _approved_open_sessions(root)
    state_root = published_state_root or snapshot_root or root / "data/phase_1c"
    executor = incremental_executor or build_raw_incremental_executor(root, clock=clock)
    effective_clock=clock or (lambda: datetime.now().astimezone())
    adapters = tuple(_PinnedAdapter(state_root, kind, sessions, executor, effective_clock) for kind in (
        "security_master", "daily_bar", "daily_security_status",
        "corporate_action", "financial_disclosure",
    ))
    return RefreshService(
        _PinnedCalendarAdapter(state_root, sessions, executor), adapters,
        SnapshotStore(state_root),
        effective_clock,
    )
