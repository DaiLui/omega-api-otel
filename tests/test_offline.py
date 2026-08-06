"""
omega-api-otel · offline tests.

No network, no live judge. Assert the ratified field cut (SPEC PACKS #4 v0.2 §3/§1b), not the wording.
Run: python tests/test_offline.py
"""
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omega_api.models import Decision, Gate  # noqa: E402

from omega_api_otel import EVALUATION_NAME, EVENT_NAME, decision_to_event  # noqa: E402
from omega_api_otel.semconv import (  # noqa: E402
    ALLOWED_KEYS,
    ATTR_CONVERSATION_ID,
    ATTR_EVALUATION_NAME,
    ATTR_SCORE_LABEL,
    FORBIDDEN_KEYS,
    OMEGA_GATE_ACTION,
    OMEGA_JUDGED,
    OMEGA_REASON_FAMILY,
    OMEGA_SIDE,
    OMEGA_TURN_ID,
)

SCORE_VALUE = "gen_ai.evaluation.score.value"


def _judged(decision="PROCEED", action="none"):
    """A judged Decision carrying fields we must NOT emit (verdict letter, plan_tier, operator_enabled)."""
    return Decision(
        turn_id="t_1",
        decision=decision,
        reason_family="ok",
        side="coupling",
        gate=Gate(action=action, release_original=action in ("none", "release"),
                  verdict="S", plan_tier="SHADOW", operator_enabled=False),
        idempotent_replay=False,
        judged=True,
    )


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_event_name_and_eval_name():
    name, attrs = decision_to_event(_judged(), "sess_1")
    check(name == EVENT_NAME == "gen_ai.evaluation.result", "event name must be gen_ai.evaluation.result")
    check(attrs[ATTR_EVALUATION_NAME] == EVALUATION_NAME == "omega_process_movement", "evaluation.name")


def test_judged_label_flag_and_gate():
    _, attrs = decision_to_event(_judged("CLARIFY", "clarify"), "sess_1")
    check(attrs[ATTR_SCORE_LABEL] == "CLARIFY", "score.label = decision when judged")
    check(attrs[OMEGA_JUDGED] is True, "omega.judged true when judged")
    check(attrs[OMEGA_GATE_ACTION] == "clarify", "omega.gate_action carried")
    check(attrs[OMEGA_TURN_ID] == "t_1" and attrs[OMEGA_REASON_FAMILY] == "ok" and attrs[OMEGA_SIDE] == "coupling",
          "turn_id / reason_family / side carried")


def test_score_value_never_present():
    _, attrs = decision_to_event(_judged(), "sess_1")
    check(SCORE_VALUE not in attrs, "score.value must never be present (numeric geometry ban)")


def test_conversation_id_only_when_real():
    _, a1 = decision_to_event(_judged(), "sess_x")
    check(a1[ATTR_CONVERSATION_ID] == "sess_x", "conversation.id from a real session_id")
    _, a2 = decision_to_event(_judged(), None)
    check(ATTR_CONVERSATION_ID not in a2, "conversation.id absent when session_id is None (never synthesized)")
    _, a3 = decision_to_event(_judged(), "")
    check(ATTR_CONVERSATION_ID not in a3, "conversation.id absent when session_id is empty")


def test_unjudged_is_honest_unknown():
    d = Decision.fail_open(RuntimeError("judge unreachable"))
    check(d.judged is False and d.decision == "UNKNOWN", "precondition: fail_open is unjudged UNKNOWN")
    _, attrs = decision_to_event(d, "sess_1")
    check(attrs[ATTR_SCORE_LABEL] == "UNKNOWN", "unjudged -> score.label UNKNOWN")
    check(attrs[OMEGA_JUDGED] is False, "unjudged -> omega.judged false")
    check(SCORE_VALUE not in attrs, "still no score.value on an unjudged event")


def test_only_allowed_no_forbidden_no_leaked_values():
    for d in (_judged(), Decision.fail_open(RuntimeError("x"))):
        _, attrs = decision_to_event(d, "sess_1")
        stray = set(attrs) - ALLOWED_KEYS
        check(not stray, "only allow-listed keys; stray=" + repr(sorted(stray)))
        bad = set(attrs) & FORBIDDEN_KEYS
        check(not bad, "no forbidden keys; bad=" + repr(sorted(bad)))
        # the internal verdict letter and plan_tier are on the Decision but must not leak as values
        check("SHADOW" not in attrs.values(), "plan_tier value must never be emitted")
        check(attrs.get(ATTR_SCORE_LABEL) != "S", "internal verdict letter must never become the label")


def test_emit_decision_zero_network_and_roundtrip():
    from opentelemetry._logs import get_logger
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor

    from omega_api_otel import emit_decision

    exp = InMemoryLogRecordExporter()
    prov = LoggerProvider()
    prov.add_log_record_processor(SimpleLogRecordProcessor(exp))
    logger = get_logger("omega-api-otel", logger_provider=prov)

    # block all socket creation for the duration of emit_decision to prove zero network I/O
    orig_socket = socket.socket

    def _no_net(*a, **k):
        raise RuntimeError("emit_decision must not open a socket")

    socket.socket = _no_net
    try:
        emit_decision(_judged("STOP", "suppress"), session_id="sess_1", logger=logger)
    finally:
        socket.socket = orig_socket

    recs = exp.get_finished_logs()
    check(len(recs) == 1, "exactly one event emitted")
    lr = recs[0].log_record
    check(lr.event_name == "gen_ai.evaluation.result", "event_name set on the emitted record")
    a = dict(lr.attributes)
    check(a[ATTR_SCORE_LABEL] == "STOP", "label round-trips through the pipeline")
    check(a[OMEGA_GATE_ACTION] == "suppress", "gate_action round-trips")
    check(SCORE_VALUE not in a, "no score.value on the emitted record")


def run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  " + fn.__name__)
    print("\n%d/%d passed" % (len(fns), len(fns)))


if __name__ == "__main__":
    run()
