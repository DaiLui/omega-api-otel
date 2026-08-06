"""
omega-api-otel · OpenTelemetry instrumentation for Omega-API evaluation events.

Put the judge's verdict into the observability stream without turning the verdict into a metric.
Emit Omega-API decisions as OpenTelemetry evaluation events: label, reason, side, and gate — never geometry.

This package is an EMITTER, not an exporter: it produces a single gen_ai.evaluation.result event per
judged turn and hands it to the OpenTelemetry pipeline you already run. It hosts no collector, no
backend, no OTLP exporter, no dashboard, no storage.
"""
from .emitter import emit_decision, judge_and_emit
from .semconv import (
    ALLOWED_KEYS,
    EVALUATION_NAME,
    EVENT_NAME,
    SEMCONV_GENAI_COMMIT,
    SEMCONV_GENAI_REPO,
    decision_to_event,
)

__version__ = "0.1.0"

__all__ = [
    "emit_decision",
    "judge_and_emit",
    "decision_to_event",
    "EVENT_NAME",
    "EVALUATION_NAME",
    "ALLOWED_KEYS",
    "SEMCONV_GENAI_REPO",
    "SEMCONV_GENAI_COMMIT",
    "__version__",
]
