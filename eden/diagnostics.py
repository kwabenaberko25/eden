"""
Eden — Startup Diagnostics

Reports the operational state of all optional subsystems at application startup.
Ensures operators are aware of silent fallbacks and missing dependencies, eliminating
the class of bugs where the app silently runs in a degraded mode without anyone knowing.

Usage:
    from eden.diagnostics import StartupDiagnostics

    diagnostics = StartupDiagnostics()
    diagnostics.register("Task Broker", "ok", "Redis-backed")
    diagnostics.register("Distributed Backend", "degraded", "No Redis — using in-memory")
    diagnostics.report()

Output:
    ─── Eden Startup Diagnostics ───
      ✅ Task Broker: Redis-backed
      ⚠️  Distributed Backend: DEGRADED — No Redis — using in-memory
    ─── 0 failed, 1 degraded subsystem(s). Review configuration. ───
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger("eden.diagnostics")

# Valid status levels for subsystem registration
SubsystemStatus = Literal["ok", "degraded", "failed"]


class StartupDiagnostics:
    """
    Collects and reports the operational state of subsystems at startup.
    
    Each subsystem registers with a name, status (ok/degraded/failed), and
    optional detail string. At the end of startup, call report() to log
    the full state to the application logger.
    
    This replaces the pattern of silently catching exceptions and continuing,
    making fallback behavior explicit and visible to operators.
    
    Example:
        >>> diag = StartupDiagnostics()
        >>> diag.register("Database", "ok", "PostgreSQL connected")
        >>> diag.register("Cache", "degraded", "Redis unavailable, using in-memory")
        >>> diag.register("Payments", "failed", "Stripe API key missing")
        >>> diag.report()
        >>> assert diag.has_failures is True
        >>> assert diag.has_degraded is True
    """

    def __init__(self) -> None:
        self._subsystems: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        status: SubsystemStatus,
        detail: str = "",
    ) -> None:
        """
        Register a subsystem's operational state.
        
        Args:
            name: Human-readable subsystem identifier (e.g., "Task Broker")
            status: One of "ok", "degraded", or "failed"
            detail: Optional detail string explaining the current state
        
        Raises:
            ValueError: If status is not one of the valid levels
        """
        if status not in ("ok", "degraded", "failed"):
            raise ValueError(
                f"Invalid status {status!r}. Must be 'ok', 'degraded', or 'failed'."
            )
        self._subsystems.append({
            "name": name,
            "status": status,
            "detail": detail,
        })

    @property
    def has_failures(self) -> bool:
        """True if any subsystem reported 'failed' status."""
        return any(s["status"] == "failed" for s in self._subsystems)

    @property
    def has_degraded(self) -> bool:
        """True if any subsystem reported 'degraded' status."""
        return any(s["status"] == "degraded" for s in self._subsystems)

    @property
    def summary(self) -> dict[str, int]:
        """Return a count of subsystems by status."""
        return {
            "ok": sum(1 for s in self._subsystems if s["status"] == "ok"),
            "degraded": sum(1 for s in self._subsystems if s["status"] == "degraded"),
            "failed": sum(1 for s in self._subsystems if s["status"] == "failed"),
        }

    def report(self) -> None:
        """
        Log a comprehensive startup report.
        
        Groups subsystems by status (ok → degraded → failed) and logs
        each with an appropriate level (INFO/WARNING/ERROR).
        
        If all subsystems are healthy, logs a single summary line.
        If any are degraded or failed, logs a prominent warning.
        """
        healthy = [s for s in self._subsystems if s["status"] == "ok"]
        degraded = [s for s in self._subsystems if s["status"] == "degraded"]
        failed = [s for s in self._subsystems if s["status"] == "failed"]

        logger.info("─── Eden Startup Diagnostics ───")

        for s in healthy:
            logger.info("  ✅ %s: %s", s["name"], s["detail"] or "OK")

        for s in degraded:
            logger.warning(
                "  ⚠️  %s: DEGRADED — %s", s["name"], s["detail"]
            )

        for s in failed:
            logger.error(
                "  ❌ %s: FAILED — %s", s["name"], s["detail"]
            )

        if degraded or failed:
            logger.warning(
                "─── %d degraded, %d failed subsystem(s). "
                "Review configuration. ───",
                len(degraded),
                len(failed),
            )
        else:
            logger.info(
                "─── All %d subsystem(s) healthy ───", len(healthy)
            )

    def reset(self) -> None:
        """Clear all registered subsystems (for testing)."""
        self._subsystems.clear()
