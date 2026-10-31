"""Private request retry policy; diagnostics contain only allowlisted values."""

import errno
import math
import time
from dataclasses import dataclass

import httpx
from tenacity import Retrying, retry_if_exception_type, wait_exponential_jitter

from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.observability import get_logger


class TransientFailure(Exception):
    def __init__(self, category, status=None):
        super().__init__(category)
        self.category = category
        self.status = status


def is_reset(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, ConnectionResetError) or (
            isinstance(error, OSError) and error.errno == errno.ECONNRESET
        ):
            return True
        error = error.__cause__ or error.__context__
    return False


def transient_transport(error):
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    if is_reset(error):
        return "connection_reset"
    return None


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    initial: float = 1
    maximum: float = 8
    jitter: float = 1

    def __post_init__(self):
        if type(self.max_attempts) is not int or self.max_attempts <= 0:
            raise ValueError("attempt count must be a positive integer")
        if any(not math.isfinite(value) for value in (self.initial, self.maximum, self.jitter)):
            raise ValueError("retry delays must be finite")
        if self.initial <= 0 or self.maximum < self.initial or self.jitter < 0:
            raise ValueError("invalid retry delays")

    def run(self, action, deadline, **context):
        started = time.monotonic()
        logger = get_logger(__name__)
        attempts = 0
        outcome = "deadline"

        def stop(state):
            nonlocal outcome
            if state.attempt_number >= self.max_attempts:
                outcome = "exhausted"
                return True
            if time.monotonic() + state.upcoming_sleep >= deadline:
                outcome = "deadline"
                return True
            return False

        def before_sleep(state):
            logger.info(
                "memory_request_wait",
                attempt=state.attempt_number,
                delay=state.next_action.sleep,
                **context,
            )

        try:
            for attempt in Retrying(
                retry=retry_if_exception_type(TransientFailure),
                wait=wait_exponential_jitter(
                    multiplier=self.initial, max=self.maximum, jitter=self.jitter
                ),
                stop=stop,
                sleep=lambda delay: time.sleep(delay),
                before_sleep=before_sleep,
                reraise=True,
            ):
                with attempt:
                    if time.monotonic() >= deadline:
                        outcome = "deadline"
                        raise MemoryStoreUnavailable(
                            "memory operation unavailable: deadline exceeded"
                        )
                    attempts = attempt.retry_state.attempt_number
                    try:
                        result = action()
                    except TransientFailure as error:
                        logger.info(
                            "memory_request_attempt",
                            attempt=attempts,
                            outcome="retryable",
                            category=error.category,
                            status=error.status,
                            **context,
                        )
                        raise
                    except (MemoryStoreRejected, MemoryStoreUnavailable) as error:
                        outcome = (
                            "rejected" if isinstance(error, MemoryStoreRejected) else "unavailable"
                        )
                        logger.info(
                            "memory_request_attempt", attempt=attempts, outcome=outcome, **context
                        )
                        raise
                    else:
                        outcome = "success"
                        logger.info(
                            "memory_request_attempt", attempt=attempts, outcome=outcome, **context
                        )
                        return result
        except TransientFailure:
            raise MemoryStoreUnavailable("memory operation unavailable") from None
        finally:
            logger.info(
                "memory_request_finished",
                attempts=attempts,
                outcome=outcome,
                elapsed_ms=(time.monotonic() - started) * 1000,
                **context,
            )
