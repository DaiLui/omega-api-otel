"""
omega_api_otel.emitter · the two public entry points.

    emit_decision(decision, session_id=...)     the pure pixel + one OTel emit · zero network · no API key
    judge_and_emit(input=..., output=..., ...)   convenience · reuse omega-api to judge, then emit

The judge stays on the Omega-API server. This pack never re-implements or derives a verdict; it
translates an omega_api.Decision that already exists into a single gen_ai.evaluation.result event.
It configures no OpenTelemetry provider and no exporter — it emits into the pipeline the caller owns.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from opentelemetry._logs import LogRecord, get_logger

from .semconv import decision_to_event

__all__ = ["emit_decision", "judge_and_emit"]

_INSTRUMENTATION_NAME = "omega-api-otel"
_INSTRUMENTATION_VERSION = "0.1.0"

TextField = Optional[Union[str, dict]]


def emit_decision(decision: Any, *, session_id: Optional[str] = None, logger: Any = None) -> None:
    """Emit one gen_ai.evaluation.result event for a Decision already in hand. Zero network.

    Pass an OpenTelemetry logger, or leave it None to resolve one from the globally configured
    provider. If no provider is configured, OpenTelemetry's no-op logger is used and nothing is
    exported — the same fail-quiet behaviour any OTel instrumentation has when the application has
    not set up a pipeline. This function performs no HTTP call and needs no API key.
    """
    event_name, attributes = decision_to_event(decision, session_id)
    log = logger if logger is not None else get_logger(_INSTRUMENTATION_NAME, _INSTRUMENTATION_VERSION)
    log.emit(LogRecord(event_name=event_name, attributes=attributes))


def judge_and_emit(
    input: TextField = None,
    output: TextField = None,
    *,
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    privacy_mode: Optional[str] = None,
    omega: Any = None,
    logger: Any = None,
    fail_open: bool = False,
) -> Any:
    """Judge one turn via omega-api, emit the evaluation event, and return the Decision.

    `omega` is an omega_api.Omega instance; if None, one is constructed (it reads OMEGA_API_KEY from
    the environment). `fail_open=True` uses omega.judge_or_release (a client policy): on a
    transport/server error it returns an unjudged Decision, which this pack emits honestly as
    score.label="UNKNOWN", omega.judged=false.

    conversation.id is populated only when you pass session_id (a real conversation identity). If you
    omit it, the judge call still works (the server assigns a session), but the event carries no
    conversation.id rather than a synthesized one.
    """
    if omega is None:
        from omega_api import Omega  # lazy · emit_decision needs neither omega-api nor a key

        omega = Omega()

    judge = omega.judge_or_release if fail_open else omega.judge
    decision = judge(
        input, output, session_id=session_id, turn_id=turn_id, privacy_mode=privacy_mode
    )
    emit_decision(decision, session_id=session_id, logger=logger)
    return decision
