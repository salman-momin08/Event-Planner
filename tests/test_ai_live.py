"""Opt-in integration test against a real Hugging Face provider.

Skipped unless HF_TOKEN (and HF_MODEL_ID or HF_ENDPOINT_URL) are set, so the default suite stays
hermetic. Run it to verify the live model path end to end:

    $env:HF_TOKEN="hf_..."; $env:HF_MODEL_ID="meta-llama/Llama-3.1-8B-Instruct"
    python -m pytest tests/test_ai_live.py -q
"""
from __future__ import annotations

import os

import pytest

_HAS_CREDS = bool(os.environ.get("HF_TOKEN")) and bool(
    os.environ.get("HF_MODEL_ID") or os.environ.get("HF_ENDPOINT_URL")
)

pytestmark = pytest.mark.skipif(
    not _HAS_CREDS, reason="set HF_TOKEN and HF_MODEL_ID/HF_ENDPOINT_URL to run the live AI test"
)

_HF_ENV_KEYS = (
    "HF_TOKEN",
    "HUGGINGFACEHUB_API_TOKEN",
    "HF_MODEL_ID",
    "HF_ENDPOINT_URL",
    "HF_PROVIDER",
    "AI_TIMEOUT_SECONDS",
    "AI_MAX_OUTPUT_TOKENS",
)


def _live_env() -> dict[str, str]:
    return {k: os.environ[k] for k in _HF_ENV_KEYS if os.environ.get(k)}


def test_live_model_produces_a_valid_applicable_draft(make_app):
    app = make_app(env=_live_env())
    assert app.app.state.ctx.ai.available, "AI should be enabled when live credentials are present"

    c = app.sign_up()
    ev = app.make_event(c, budgetCents=2_500_000, eventDate="2027-06-12")
    base = f"/events/{ev['id']}"

    draft = c.post(f"{base}/ai/plans", {"preferences": "rustic outdoor wedding, vegetarian menu"})
    assert draft.status == 201, draft.text
    plan = draft.json["plan"]

    # The workflow guarantees a schema-valid, business-rule-checked plan regardless of the raw model text.
    assert plan["summary"]
    assert len(plan["themes"]) >= 1
    assert plan["budgetAllocations"] and sum(b["percent"] for b in plan["budgetAllocations"]) <= 100.01
    assert plan["tasks"]
    titles = [t["title"].lower() for t in plan["tasks"]]
    assert len(titles) == len(set(titles)), "task titles must be unique"

    applied = c.post(f"{base}/ai/plans/{draft.json['id']}/apply")
    assert applied.status == 200, applied.text
    assert applied.json["tasksCreated"] >= 1
    # Amounts are computed by the app, never by the model.
    assert applied.json["unallocatedCents"] <= ev["budgetCents"]
