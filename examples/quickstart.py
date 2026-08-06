"""
omega-api-otel · quickstart.

Configure your own OpenTelemetry pipeline, then emit one Omega-API judgment as an evaluation event.
This example prints the event to the console via the OTel SDK; in production you point the SDK at
your own backend (the pipeline is yours, not this package's).
"""
import os

from opentelemetry._logs import get_logger, set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor

from omega_api import Omega
from omega_api_otel import emit_decision

# --- your OpenTelemetry pipeline (you own this) ---
provider = LoggerProvider()
provider.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter()))
set_logger_provider(provider)
logger = get_logger("omega-api-otel", logger_provider=provider)

# --- judge one turn, then emit the evaluation event ---
omega = Omega(api_key=os.environ["OMEGA_API_KEY"])
decision = omega.judge(
    input="Can you book me a flight to Rome?",
    output="Sure — departing when, and from which city?",
    session_id="conv-demo-1",
)
emit_decision(decision, session_id="conv-demo-1", logger=logger)
print("decision:", decision.decision, "| gate:", decision.gate.action)
