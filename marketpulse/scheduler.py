"""Weekly scheduler for automated market intelligence updates."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from marketpulse.contracts import (
    FeatureFlags,
    MarketPulseState,
    ScheduleConfig,
    ScheduleExecution,
    ScheduleHistory,
)
from marketpulse.graph import MarketPulseWorkflow


@dataclass
class SchedulerState:
    """Internal state for the scheduler."""

    is_running: bool = False
    current_thread: threading.Thread | None = None
    execution_queue: deque[ScheduleExecution] = field(default_factory=deque)
    last_execution_time: datetime | None = None
    next_scheduled_time: datetime | None = None
    execution_count: int = 0


class SchedulerEngine:
    """Core scheduling engine for automated executions."""

    def __init__(
        self,
        config: ScheduleConfig,
        workflow: MarketPulseWorkflow,
    ) -> None:
        self.config = config
        self.workflow = workflow
        self.state = SchedulerState()
        self.history = ScheduleHistory()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self.state.is_running:
                return

            self.state.is_running = True
            self._stop_event.clear()

            # Calculate next scheduled time
            self.state.next_scheduled_time = self._calculate_next_schedule()

            # Start scheduler thread
            self.state.current_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="MarketPulseScheduler"
            )
            self.state.current_thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        with self._lock:
            if not self.state.is_running:
                return

            self.state.is_running = False
            self._stop_event.set()

            if self.state.current_thread:
                self.state.current_thread.join(timeout=5.0)
                self.state.current_thread = None

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        with self._lock:
            return self.state.is_running

    def get_next_execution_time(self) -> datetime | None:
        """Get the next scheduled execution time."""
        with self._lock:
            return self.state.next_scheduled_time

    def get_execution_history(self) -> ScheduleHistory:
        """Get execution history."""
        with self._lock:
            return self.history

    def execute_now(self) -> ScheduleExecution:
        """Execute workflow immediately."""
        execution_id = self._generate_execution_id()
        start_time = datetime.now()

        try:
            # Create a simple state for execution
            from marketpulse.data import load_market_records
            from pathlib import Path

            records = load_market_records(Path("data/sample_market.csv"))

            state = MarketPulseState(
                question="Scheduled market intelligence update",
                competitors=["AlphaMart", "BetaBuy", "Cartly"],
                records=records,
                feature_flags=FeatureFlags(
                    enable_social_worker=True,
                    enable_pricing_delta=True,
                    enable_weekly_scheduler=True,
                ),
            )

            # Execute workflow
            result = self.workflow.run(state)

            # Calculate duration
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Create execution record
            execution = ScheduleExecution(
                execution_id=execution_id,
                scheduled_time=start_time,
                actual_time=start_time,
                completion_time=end_time,
                status="success",
                duration_ms=duration_ms,
                error_message=None,
                competitors=result.competitors,
                records_processed=len(result.records),
                feature_flags={
                    "enable_social_worker": result.feature_flags.enable_social_worker,
                    "enable_pricing_delta": result.feature_flags.enable_pricing_delta,
                    "enable_weekly_scheduler": result.feature_flags.enable_weekly_scheduler,
                },
            )

            # Update history
            self.history.add_execution(execution)

            return execution

        except Exception as e:
            # Handle execution failure
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            execution = ScheduleExecution(
                execution_id=execution_id,
                scheduled_time=start_time,
                actual_time=start_time,
                completion_time=end_time,
                status="failed",
                duration_ms=duration_ms,
                error_message=str(e),
                competitors=[],
                records_processed=0,
                feature_flags={},
            )

            self.history.add_execution(execution)
            return execution

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                # Check if it's time to execute
                now = datetime.now()

                with self._lock:
                    next_time = self.state.next_scheduled_time

                if next_time and now >= next_time:
                    # Execute scheduled task
                    self.execute_now()

                    # Calculate next schedule
                    with self._lock:
                        self.state.next_scheduled_time = self._calculate_next_schedule()

                # Sleep for a short interval
                self._stop_event.wait(timeout=60)  # Check every minute

            except Exception as e:
                # Log error but continue running
                print(f"Scheduler error: {e}")
                time.sleep(60)

    def _calculate_next_schedule(self) -> datetime:
        """Calculate next scheduled execution time."""
        now = datetime.now()

        if self.config.frequency == "hourly":
            # Next hour
            next_time = now.replace(minute=0, second=0, microsecond=0)
            next_time += timedelta(hours=1)

        elif self.config.frequency == "daily":
            # Next day at specified hour
            next_time = now.replace(hour=self.config.hour, minute=0, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)

        elif self.config.frequency == "weekly":
            # Next specified day at specified hour
            next_time = now.replace(hour=self.config.hour, minute=0, second=0, microsecond=0)

            # Find next occurrence of specified day
            days_ahead = (self.config.day_of_week - now.weekday()) % 7
            if days_ahead == 0 and next_time <= now:
                days_ahead = 7

            next_time += timedelta(days=days_ahead)

        else:
            # Default to daily
            next_time = now.replace(hour=self.config.hour, minute=0, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)

        return next_time

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        count = self.state.execution_count + 1
        return f"exec_{timestamp}_{count}"


class ScheduleManager:
    """High-level manager for scheduling operations."""

    def __init__(self, workflow: MarketPulseWorkflow) -> None:
        self.workflow = workflow
        self.scheduler: SchedulerEngine | None = None
        self.config = ScheduleConfig()

    def configure_schedule(self, config: ScheduleConfig) -> None:
        """Configure the schedule."""
        self.config = config

        # Restart scheduler if running
        if self.scheduler and self.scheduler.is_running():
            self.scheduler.stop()
            self.scheduler = SchedulerEngine(config, self.workflow)
            if config.enabled:
                self.scheduler.start()

    def start_scheduler(self) -> None:
        """Start the scheduler with current configuration."""
        if not self.config.enabled:
            raise RuntimeError("Scheduler is not enabled in configuration")

        if self.scheduler and self.scheduler.is_running():
            return

        self.scheduler = SchedulerEngine(self.config, self.workflow)
        self.scheduler.start()

    def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.stop()

    def is_scheduler_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.is_running() if self.scheduler else False

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status."""
        status = {
            "enabled": self.config.enabled,
            "running": self.is_scheduler_running(),
            "config": self.config.model_dump(),
            "next_execution": None,
            "history": None,
        }

        if self.scheduler:
            status["next_execution"] = self.scheduler.get_next_execution_time()
            status["history"] = self.scheduler.get_execution_history()

        return status

    def execute_immediate(self) -> ScheduleExecution:
        """Execute an immediate workflow run."""
        if not self.scheduler:
            self.scheduler = SchedulerEngine(self.config, self.workflow)

        return self.scheduler.execute_now()


def create_schedule_manager(workflow: MarketPulseWorkflow) -> ScheduleManager:
    """Create a schedule manager with default configuration."""
    return ScheduleManager(workflow)