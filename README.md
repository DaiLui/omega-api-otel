# omega-api-otel

**OpenTelemetry instrumentation for Ω-API evaluation events.**

> Put the judge's verdict into the observability stream without turning the verdict into a metric.

Emit Ω-API decisions as OpenTelemetry evaluation events: label, reason, side, and gate — never geometry.

This is an **emitter**, not an exporter. It turns each Ω-API judgment into one
`gen_ai.evaluation.result` event and hands it to the OpenTelemetry pipeline you already run.
It hosts no collector, no backend, no OTLP exporter, no dashboard, and no storage — those stay yours.

## Install

```
pip install omega-api-otel
```

Depends on `omega-api` and `opentelemetry-api`. Your application owns the OpenTelemetry SDK and
decides where events go.

## Use

You already have a `Decision` from `omega-api`:

```python
from omega_api import Omega
from omega_api_otel import emit_decision

omega = Omega()  # reads OMEGA_API_KEY
decision = omega.judge(input=user_msg, output=agent_reply, session_id="conv-42")

emit_decision(decision, session_id="conv-42")
# -> one gen_ai.evaluation.result event on your OTel pipeline
```

Or judge and emit in one call:

```python
from omega_api_otel import judge_and_emit

decision = judge_and_emit(input=user_msg, output=agent_reply, session_id="conv-42")
```

`emit_decision` performs no network I/O and needs no API key — it maps a decision you already have.
`judge_and_emit` reuses `omega-api` for the HTTP call, then emits.

## Reading agents together (Hive)

A Hive draws the relation of two agents **only** from a shared token in `turn_id`, set **before** the run.
Timing can only suggest an association; it never certifies one. Without the token each agent is still judged normally.

```
turn_id = {agent}_{run_token}_{nnn}
agent      your label · [a-z0-9-]
run_token  10 lowercase hex · one per PAIR of agents, per run · new run = new token
nnn        3 digits shared by both agents for the same exchange (agents counting on their own: s001 · declared, not aligned · no relation graph)
```

Rules: one `session_id` per agent for the whole token (a restart needs a new token) · three agents on one token are not certified ·
a re-used `turn_id` for a different turn returns `409 TURN_CONFLICT` and the turn is **not recorded**. Full rules: [omega.dailui.com/integrations.php](https://omega.dailui.com/integrations.php) and your account's Integration page.

`judge_and_emit(..., session_id=..., turn_id=...)` passes `turn_id` through to the Python client; always pass `session_id` for a Hive member.

## What lands on the event

```
event  gen_ai.evaluation.result
  gen_ai.evaluation.name        "omega_process_movement"
  gen_ai.evaluation.score.label PROCEED | CLARIFY | STOP | UNKNOWN
  gen_ai.conversation.id        your session_id (only when you pass one)
  omega.turn_id                 the turn id the server assigned
  omega.reason_family           drift | security | residue | missing_limit | ok | unknown
  omega.side                    user | agent | coupling | unknown
  omega.gate_action             release | clarify | suppress | none
  omega.judged                  true, or false for a fail-open synthetic decision
```

There is no numeric score on the event. Omega-API measures whether the **process** moved on each
turn; it does not tell you whether the agent reached the user's goal. Read the label and the gate,
act on the gate before showing the reply, and read outcome separately through your own events.

Unreachable judge with `judge_and_emit(..., fail_open=True)`: the event is emitted honestly with
`score.label="UNKNOWN"` and `omega.judged=false`, never a fabricated verdict.

## Note on the convention

The GenAI evaluation event is part of the OpenTelemetry GenAI semantic conventions, which are
currently in **Development** status. The convention strings this package emits are pinned to a
recorded commit of `open-telemetry/semantic-conventions-genai` and isolated in a single module, so
a convention change is one edit here rather than a change across your code.

## License

Apache-2.0.
