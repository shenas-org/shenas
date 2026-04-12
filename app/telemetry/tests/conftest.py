"""Shared fixtures for telemetry tests."""

import os

# Prevent init_telemetry() from starting background exporter threads.
# Uses _SHENAS_SKIP_TELEMETRY (not OTEL_SDK_DISABLED) so the tests can
# still create explicit TracerProvider/LoggerProvider instances.
os.environ["_SHENAS_SKIP_TELEMETRY"] = "1"
