"""
omega_api_otel.semconv · the ONE mapping module.

Every OpenTelemetry GenAI convention string lives here and NOWHERE else, pinned to a recorded
commit of the (Development-status) GenAI semantic conventions. Our own fields live under the
omega.* namespace — never a gen_ai.omega_* key, never our fields hidden inside gen_ai.* to look
standard.

The core is a pure function: an omega_api.Decision + a session_id -> (event_name, attributes).
Zero network. Zero OpenTelemetry. Zero judge logic. It only projects a verdict that already exists
into the evaluation-event shape, as a label — never a number.

Pinned convention source (re-verify on-source before any version bump):
    repo   open-telemetry/semantic-conventions-genai
    file   docs/gen-ai/gen-ai-events.md   (event: gen_ai.evaluation.result)
    commit c739977ae690961f36e435504e5c1febaef1f7f3   (2026-07-30)
All GenAI-specific keys below are Status: Development in that repo; they can change under us.
That is exactly why they are isolated here, behind one module.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

SEMCONV_GENAI_REPO = "open-telemetry/semantic-conventions-genai"
SEMCONV_GENAI_COMMIT = "c739977ae690961f36e435504e5c1febaef1f7f3"  # pin · re-verify on-source before a bump

# --- gen_ai.* keys · verbatim from the pinned semconv · defined ONLY here --------------------
EVENT_NAME = "gen_ai.evaluation.result"          # the event name MUST be exactly this
ATTR_EVALUATION_NAME = "gen_ai.evaluation.name"  # Required
ATTR_SCORE_LABEL = "gen_ai.evaluation.score.label"  # low-cardinality string
ATTR_CONVERSATION_ID = "gen_ai.conversation.id"  # only from a real session id · never synthesized
# NOTE · gen_ai.evaluation.score.value is a `double` in the semconv. It is DELIBERATELY not
# defined here and never emitted: a number would turn the verdict into a metric (Ω→Ø).

# --- our evaluation name · we own its meaning · stable --------------------------------------
EVALUATION_NAME = "omega_process_movement"

# --- omega.* keys · our namespace -----------------------------------------------------------
OMEGA_TURN_ID = "omega.turn_id"
OMEGA_REASON_FAMILY = "omega.reason_family"
OMEGA_SIDE = "omega.side"
OMEGA_GATE_ACTION = "omega.gate_action"
OMEGA_JUDGED = "omega.judged"

# --- the allow-list · exactly the keys this pack may ever emit -------------------------------
ALLOWED_KEYS = frozenset({
    ATTR_EVALUATION_NAME, ATTR_SCORE_LABEL, ATTR_CONVERSATION_ID,
    OMEGA_TURN_ID, OMEGA_REASON_FAMILY, OMEGA_SIDE, OMEGA_GATE_ACTION, OMEGA_JUDGED,
})

# --- keys/values that must NEVER appear · belt-and-suspenders for the tests -----------------
FORBIDDEN_KEYS = frozenset({
    "gen_ai.evaluation.score.value",
    "sigma", "omega", "σ", "ω", "R_mean", "distance", "csm", "CSM",
    "plan_tier", "operator_enabled", "verdict",
    "gen_ai.input.messages", "gen_ai.output.messages",
})

UNKNOWN_LABEL = "UNKNOWN"


def decision_to_event(decision: Any, session_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """Project one omega_api.Decision into (event_name, attributes).

    Pure: no I/O, no OpenTelemetry, no judge logic. Implements the ratified field cut and the
    unjudged rule (SPEC PACKS #4 v0.2 §1b):

        judged is True  -> score.label = decision.decision ; omega.judged = true
        judged is False -> score.label = "UNKNOWN"         ; omega.judged = false   (fail-open synthetic)

    conversation.id is populated ONLY from a real, non-empty session_id (never a UUID / trace-id /
    hash fallback). Only the allow-listed keys are ever produced; the internal verdict letter
    (S/1/Ø), plan_tier, operator_enabled and any numeric geometry the Decision may carry are dropped.
    """
    judged = bool(getattr(decision, "judged", True))
    label = decision.decision if judged else UNKNOWN_LABEL

    gate = getattr(decision, "gate", None)
    attrs: Dict[str, Any] = {
        ATTR_EVALUATION_NAME: EVALUATION_NAME,
        ATTR_SCORE_LABEL: label,
        OMEGA_TURN_ID: getattr(decision, "turn_id", "") or "",
        OMEGA_REASON_FAMILY: getattr(decision, "reason_family", "unknown") or "unknown",
        OMEGA_SIDE: getattr(decision, "side", "unknown") or "unknown",
        OMEGA_GATE_ACTION: getattr(gate, "action", "none") or "none",
        OMEGA_JUDGED: judged,
    }
    if session_id:  # real identity only · never synthesized
        attrs[ATTR_CONVERSATION_ID] = session_id

    # allow-list guard · by construction we only set allowed keys; assert it so a careless edit fails a test
    stray = set(attrs) - ALLOWED_KEYS
    if stray:
        raise AssertionError(
            "omega-api-otel: non-allow-listed attribute(s) would be emitted: " + repr(sorted(stray))
        )
    return EVENT_NAME, attrs
