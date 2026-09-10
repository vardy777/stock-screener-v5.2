from datetime import datetime, timezone

from v5_2.data.checkpoints import CheckpointStore
from v5_2.data.raw_artifacts import RawArtifactStore
from v5_2.data.real_audits.corporate_action_acquisition import acquire_corporate_action_requests
from v5_2.providers.contracts import ProviderRequestV1
from v5_2.providers.credentials import load_datahub_credential
from v5_2.providers.tushare import ProviderPageV1


class Client:
    def fetch_page(self, request, credential, *, page_identity):
        return ProviderPageV1(request_id=request.request_id, page_identity=page_identity,
            response_code=0, response_status="ok", rows=({"ts_code": "600000.SH"},),
            has_more=False, total_count=1)


class Limiter:
    min_interval_seconds = 0.0
    def acquire(self, clock, sleeper): return None


def test_acquisition_is_checkpointed_and_idempotently_resumable(tmp_path):
    request = ProviderRequestV1.create(
        source_name="datahubco_tushare_proxy", dataset_kind="corporate_action", endpoint="dividend",
        parameters={"ts_code": "600000.SH"}, requested_fields=("ts_code",), page_size=10,
        request_policy_version="phase-1b2c-corporate-action-v1")
    kwargs = dict(client=Client(), credential=load_datahub_credential(env={"DATAHUB_API_KEY": "sentinel"}),
        raw_store=RawArtifactStore(tmp_path), checkpoint_store=CheckpointStore(tmp_path), limiter=Limiter(),
        utc_clock=lambda: datetime(2026, 9, 10, tzinfo=timezone.utc))
    first = acquire_corporate_action_requests((request,), resume=False, **kwargs)
    second = acquire_corporate_action_requests((request,), resume=True, **kwargs)
    assert first.payload_hashes == second.payload_hashes
    assert len(tuple((tmp_path / "raw").rglob("*.json"))) == 1

