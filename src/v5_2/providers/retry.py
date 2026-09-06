from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")


class TransientProviderError(RuntimeError):
    """A sanitized error eligible for retry."""


class PermanentProviderError(RuntimeError):
    """A sanitized error that must fail immediately."""


@dataclass(frozen=True, slots=True)
class RetryPolicyV1:
    max_attempts: int
    base_delay_seconds: float
    max_delay_seconds: float
    policy_version: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts <= 0
        ):
            raise ValueError("max_attempts must be a positive integer")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must be non-negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max retry delay cannot be below base delay")
        if not self.policy_version:
            raise ValueError("policy_version must not be empty")

    def run(self, operation: Callable[[], T], sleeper: Callable[[float], None]) -> T:
        for attempt in range(self.max_attempts):
            try:
                return operation()
            except TransientProviderError:
                if attempt + 1 >= self.max_attempts:
                    raise
                delay = min(
                    self.base_delay_seconds * (2**attempt), self.max_delay_seconds
                )
                sleeper(delay)
        raise AssertionError("retry loop exhausted without returning or raising")
