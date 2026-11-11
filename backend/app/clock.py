"""
Deterministic clock and temporal service for GuardSLM LMS.
Supports injectable simulation time via headers, context variables, and testing overrides.
"""
from datetime import datetime, timezone
from typing import Optional
from contextvars import ContextVar
from fastapi import Request

_simulated_time_var: ContextVar[Optional[datetime]] = ContextVar("simulated_time", default=None)


def parse_iso_datetime(dt_str: str) -> datetime:
    """
    Parse an ISO-8601 datetime string strictly.
    Raises ValueError on invalid format rather than silently returning current time.
    """
    if not dt_str or not isinstance(dt_str, str):
        raise ValueError("Datetime string must be a non-empty string.")

    clean = dt_str.strip().replace("Z", "+00:00")
    try:
        if "T" in clean:
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.fromisoformat(clean + "T00:00:00+00:00")
    except Exception as e:
        raise ValueError(f"Invalid ISO-8601 datetime format '{dt_str}': {e}") from e

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Clock:
    """Deterministic time provider."""

    @staticmethod
    def now(request: Optional[Request] = None) -> datetime:
        """
        Get current effective time. Checks:
        1. Explicit context override (for testing/simulations)
        2. HTTP request header 'X-Simulation-Time'
        3. Real system time in UTC
        """
        # 1. Context variable override
        ctx_time = _simulated_time_var.get()
        if ctx_time is not None:
            return ctx_time

        # 2. HTTP header simulation
        if request is not None:
            sim_header = request.headers.get("X-Simulation-Time")
            if sim_header:
                try:
                    return parse_iso_datetime(sim_header)
                except ValueError:
                    pass

        # 3. UTC system time
        return datetime.now(timezone.utc)

    # Aliases for convenience and uniform usage
    parse_iso_datetime = staticmethod(parse_iso_datetime)

    @staticmethod
    def get_time(request: Optional[Request] = None) -> datetime:
        return Clock.now(request)

    @staticmethod
    def set_simulation_time(dt: Optional[datetime]) -> None:
        """Set or clear the active context simulation timestamp."""
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        _simulated_time_var.set(dt)


class override_clock:
    """Context manager for temporary deterministic time travel during testing."""

    def __init__(self, target_time: datetime | str):
        if isinstance(target_time, str):
            self.target_time = parse_iso_datetime(target_time)
        else:
            self.target_time = target_time if target_time.tzinfo else target_time.replace(tzinfo=timezone.utc)
        self.prev_time = None

    def __enter__(self):
        self.prev_time = _simulated_time_var.get()
        Clock.set_simulation_time(self.target_time)
        return self.target_time

    def __exit__(self, exc_type, exc_val, exc_tb):
        Clock.set_simulation_time(self.prev_time)
