from __future__ import annotations

import pytest

from v5_2.providers.rate_limit import RateLimiter
from v5_2.providers.retry import (
    PermanentProviderError,
    RetryPolicyV1,
    TransientProviderError,
)


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


def test_rate_limiter_uses_injected_monotonic_time() -> None:
    time = FakeTime()
    limiter = RateLimiter(min_interval_seconds=2.0)
    limiter.acquire(time.clock, time.sleep)
    limiter.acquire(time.clock, time.sleep)
    limiter.acquire(time.clock, time.sleep)
    assert time.sleeps == [2.0, 2.0]


def test_rate_limiter_does_not_sleep_after_external_time_advance() -> None:
    time = FakeTime()
    limiter = RateLimiter(min_interval_seconds=2.0)
    limiter.acquire(time.clock, time.sleep)
    time.value = 3.0
    limiter.acquire(time.clock, time.sleep)
    assert time.sleeps == []


def test_transient_failure_retries_with_versioned_exponential_backoff() -> None:
    attempts = 0
    sleeps: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TransientProviderError("temporary")
        return "ok"

    policy = RetryPolicyV1(
        max_attempts=3,
        base_delay_seconds=1.5,
        max_delay_seconds=10.0,
        policy_version="retry-v1",
    )
    assert policy.run(operation, sleeps.append) == "ok"
    assert attempts == 3
    assert sleeps == [1.5, 3.0]


def test_retry_is_bounded_and_raises_last_sanitized_transient_error() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise TransientProviderError("temporary")

    policy = RetryPolicyV1(3, 1.0, 2.0, "retry-v1")
    with pytest.raises(TransientProviderError, match="temporary"):
        policy.run(operation, lambda _: None)
    assert attempts == 3


def test_permanent_failure_never_retries() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise PermanentProviderError("schema rejected")

    with pytest.raises(PermanentProviderError):
        RetryPolicyV1(3, 1.0, 2.0, "retry-v1").run(operation, lambda _: None)
    assert attempts == 1


@pytest.mark.parametrize("attempts", [0, -1, True])
def test_invalid_retry_attempt_limit_fails_closed(attempts: object) -> None:
    with pytest.raises(ValueError):
        RetryPolicyV1(attempts, 1.0, 2.0, "retry-v1")  # type: ignore[arg-type]
