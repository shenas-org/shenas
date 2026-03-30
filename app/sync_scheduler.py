"""Standalone sync scheduler sidecar.

Runs as a separate process alongside the server, polling the schedule
API and triggering syncs via REST calls. Start with ``shenas sync-daemon``.
"""

from __future__ import annotations

import logging
import signal
import threading

from app.cli.client import ShenasServerError

logger = logging.getLogger(__name__)


class SyncDaemon:
    """Polls the server for pipes due to sync and triggers them via REST."""

    def __init__(self, server_url: str, check_interval: int = 60) -> None:
        from app.cli.client import ShenasClient

        self.client = ShenasClient(base_url=server_url)
        self.check_interval = check_interval
        self._shutdown = threading.Event()

    def run(self) -> None:
        """Main loop. Runs until shutdown signal."""
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)

        logger.info("Sync daemon started (check interval: %ds)", self.check_interval)

        while not self._shutdown.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Error in sync daemon tick")
            self._shutdown.wait(timeout=self.check_interval)

        logger.info("Sync daemon stopped")

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Received signal %d, shutting down", signum)
        self._shutdown.set()

    def _tick(self) -> None:
        try:
            schedule = self.client.get_sync_schedule()
        except ShenasServerError:
            logger.warning("Server unreachable, will retry next interval")
            return

        due = [s for s in schedule if s.get("is_due")]
        if not due:
            return

        logger.info("Pipes due for sync: %s", ", ".join(s["name"] for s in due))
        for item in due:
            if self._shutdown.is_set():
                break
            self._sync_pipe(item["name"])

    def _sync_pipe(self, name: str) -> None:
        logger.info("Starting sync for %s", name)
        try:
            for event in self.client.sync_pipe(name):
                event_type = event.get("_event", "message")
                message = event.get("message", "")
                if event_type == "error":
                    logger.error("Sync %s: %s", name, message)
                elif event_type == "complete":
                    logger.info("Sync %s complete: %s", name, message)
                else:
                    logger.debug("Sync %s: %s", name, message)
        except ShenasServerError as exc:
            if exc.status_code == 409:
                logger.debug("Skipping %s: sync already in progress", name)
            else:
                logger.error("Sync %s failed: %s", name, exc.detail)
        except Exception:
            logger.exception("Sync %s failed", name)


def run_daemon(server_url: str, check_interval: int = 60) -> None:
    """Entry point for the sync daemon."""
    daemon = SyncDaemon(server_url=server_url, check_interval=check_interval)
    daemon.run()
