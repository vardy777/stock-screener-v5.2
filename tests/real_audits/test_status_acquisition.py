from datetime import datetime, timezone

from v5_2.data.checkpoints import CheckpointStore
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.data.real_audits.status_acquisition import acquire_status_requests
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_datahub_credential
from v5_2.providers.tushare import ProviderPageV1


class Client:
    def fetch_page(self, request, credential, *, page_identity):
        assert str(credential) == "<redacted>"
        return ProviderPageV1(
            request_id=request.request_id, page_identity=page_identity,
            response_code=0, response_status="ok",
            rows=({"ts_code": "000001.SZ"},), has_more=False, total_count=1,
        )


class Limiter:
    min_interval_seconds = 0.0

    def acquire(self, clock, sleeper):
        return None


def test_status_acquisition_writes_raw_receipt_and_checkpoint(tmp_path) -> None:
    request = ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="suspension_history", endpoint="suspend-d",
        parameters={"start_date": "20250101", "end_date": "20251231"}, requested_fields=("ts_code",),
        page_size=10, request_policy_version="phase-1b2a-status-v1",
    )
    result = acquire_status_requests(
        (request,), client=Client(), credential=load_datahub_credential(env={"DATAHUB_API_KEY": "sentinel"}),
        raw_store=RawArtifactStore(tmp_path), checkpoint_store=CheckpointStore(tmp_path),
        rate_limiter=Limiter(), utc_clock=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc), resume=False,
    )
    assert result.completed_requests == 1
    assert result.page_count == 1
    assert result.row_count == 1
    assert len(tuple((tmp_path / "raw").rglob("*.json"))) == 1
    assert len(tuple((tmp_path / "receipts").rglob("*.json"))) == 1
    assert len(tuple((tmp_path / "checkpoints").glob("*.json"))) == 1
