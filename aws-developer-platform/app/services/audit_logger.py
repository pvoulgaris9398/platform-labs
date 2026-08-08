"""Dual-write audit service with injectable sinks."""

import asyncio
from collections.abc import Awaitable, Callable

from app.schemas.audit import AuditEvent

AuditSink = Callable[[str, AuditEvent], Awaitable[None]]


class AuditWriteError(RuntimeError):
    """Raised when any immutable audit sink fails."""


async def noop_sink(_payload: str, _event: AuditEvent) -> None:
    """Development sink used until cloud adapters are configured."""


class AuditLogger:
    """Write identical event payloads concurrently to two immutable sinks."""

    def __init__(
        self, cloudwatch_sink: AuditSink = noop_sink, s3_sink: AuditSink = noop_sink
    ) -> None:
        self.cloudwatch_sink = cloudwatch_sink
        self.s3_sink = s3_sink

    async def emit(self, event: AuditEvent) -> None:
        """Emit an event and reject partial success."""

        payload = event.model_dump_json()
        results = await asyncio.gather(
            self.cloudwatch_sink(payload, event),
            self.s3_sink(payload, event),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, Exception)]
        if failures:
            raise AuditWriteError(f"audit dual-write failed: {failures[0]}")


audit_logger = AuditLogger()
