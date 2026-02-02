"""
Log aggregator for collecting request metrics and outputting periodic summaries.
Thread-safe singleton that reduces terminal log verbosity while maintaining detailed file logs.
"""
import asyncio
import re
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RequestMetrics:
    """Aggregated request metrics for a time period."""
    total_requests: int = 0
    errors: int = 0  # 5xx status codes
    warnings: int = 0  # 4xx status codes
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    total_duration_ms: float = 0.0
    slow_requests: int = 0
    paths: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def avg_duration_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests


class LogAggregator:
    """
    Thread-safe singleton that collects request metrics and outputs periodic summaries.

    Usage:
        aggregator = LogAggregator.get_instance()
        aggregator.configure(interval_seconds=60, slow_threshold_ms=1000, enabled=True)
        aggregator.start()

        # Record each request
        aggregator.record_request(status_code=200, duration_ms=45.5, path="/api/users")

        # On shutdown
        aggregator.stop()
    """

    _instance: Optional["LogAggregator"] = None
    _lock = threading.Lock()

    # Patterns to normalize paths (replace UUIDs, numeric IDs)
    UUID_PATTERN = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    NUMERIC_ID_PATTERN = re.compile(r"/\d+(?=/|$)")

    def __init__(self):
        self._metrics = RequestMetrics()
        self._metrics_lock = threading.Lock()
        self._interval_seconds = 60
        self._slow_threshold_ms = 1000
        self._enabled = True
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_instance(cls) -> "LogAggregator":
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def configure(
        self,
        interval_seconds: int = 60,
        slow_threshold_ms: int = 1000,
        enabled: bool = True
    ) -> None:
        """Configure the aggregator settings."""
        self._interval_seconds = interval_seconds
        self._slow_threshold_ms = slow_threshold_ms
        self._enabled = enabled

    def _normalize_path(self, path: str) -> str:
        """Normalize a path by replacing UUIDs and numeric IDs with placeholders."""
        # Replace UUIDs
        normalized = self.UUID_PATTERN.sub("{uuid}", path)
        # Replace numeric IDs
        normalized = self.NUMERIC_ID_PATTERN.sub("/{id}", normalized)
        return normalized

    def record_request(
        self,
        status_code: int,
        duration_ms: float,
        path: str,
    ) -> None:
        """Record a completed request's metrics."""
        if not self._enabled:
            return

        normalized_path = self._normalize_path(path)

        with self._metrics_lock:
            self._metrics.total_requests += 1
            self._metrics.status_codes[status_code] += 1
            self._metrics.total_duration_ms += duration_ms
            self._metrics.paths[normalized_path] += 1

            if status_code >= 500:
                self._metrics.errors += 1
            elif status_code >= 400:
                self._metrics.warnings += 1

            if duration_ms > self._slow_threshold_ms:
                self._metrics.slow_requests += 1

    def get_summary(self) -> Dict:
        """Get current metrics summary without resetting."""
        with self._metrics_lock:
            return {
                "total_requests": self._metrics.total_requests,
                "errors": self._metrics.errors,
                "warnings": self._metrics.warnings,
                "avg_duration_ms": round(self._metrics.avg_duration_ms(), 2),
                "slow_requests": self._metrics.slow_requests,
                "status_codes": dict(self._metrics.status_codes),
                "top_paths": dict(
                    sorted(
                        self._metrics.paths.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                ),
            }

    def flush_and_reset(self) -> Dict:
        """Get current metrics and reset counters."""
        with self._metrics_lock:
            summary = self.get_summary()
            self._metrics = RequestMetrics()
            return summary

    def _output_summary(self) -> None:
        """Output summary to console."""
        with self._metrics_lock:
            if self._metrics.total_requests == 0:
                return

            m = self._metrics
            avg_dur = m.avg_duration_ms()

            # Format status codes compactly
            status_str = ", ".join(
                f"{code}: {count}"
                for code, count in sorted(m.status_codes.items())
            )

            # Output summary line
            summary_line = (
                f"[SUMMARY] {m.total_requests} requests | "
                f"{m.errors} errors | {m.warnings} warnings | "
                f"avg {avg_dur:.1f}ms | {m.slow_requests} slow"
            )

            print("=" * 60, file=sys.stdout)
            print(summary_line, file=sys.stdout)
            if status_str:
                print(f"Status codes: {{{status_str}}}", file=sys.stdout)
            print("=" * 60, file=sys.stdout)
            sys.stdout.flush()

            # Reset metrics after output
            self._metrics = RequestMetrics()

    async def _periodic_summary_task(self) -> None:
        """Async task that outputs summaries at configured intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._interval_seconds)
                if self._running and self._enabled:
                    self._output_summary()
            except asyncio.CancelledError:
                break
            except Exception:
                # Don't let errors stop the summary task
                pass

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the periodic summary task."""
        if not self._enabled or self._running:
            return

        self._running = True
        self._loop = loop or asyncio.get_event_loop()
        self._task = self._loop.create_task(self._periodic_summary_task())

    def stop(self) -> None:
        """Stop the periodic summary task and output final summary."""
        if not self._running:
            return

        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()

        # Output final summary
        self._output_summary()


# Module-level convenience functions
def get_log_aggregator() -> LogAggregator:
    """Get the singleton LogAggregator instance."""
    return LogAggregator.get_instance()
