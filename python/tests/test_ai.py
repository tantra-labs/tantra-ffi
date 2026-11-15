"""Wheel ``tantra.ai`` surface: ask pipeline, knowledge pack, decision guard."""

from __future__ import annotations

import pytest
from tantra.ai.ask import AskResult, translate_query
from tantra.ai.decision import (
    DecisionKind,
    apply_llm_decision,
    guard_llm_decision,
    is_protective_exit,
    validate_llm_decision,
)
from tantra.ai.knowledge import KnowledgePack, build_knowledge_pack
from tantra.ai.llm.provider import ScriptedFakeLlm
from tantra.instrument import InstrumentId
from tantra.order import OrderIntent

SYM = InstrumentId("NIFTY", "NSE")
BUY = OrderIntent.market_buy(SYM, 100.0)
STOP_SELL = OrderIntent.stop_sell(SYM, 100.0, 95.0)


def _raw(**kw: object) -> dict[str, object]:
    base = {
        "order_id": "o1",
        "decision": "approve",
        "decided_quantity": 100.0,
        "rationale": "ok",
    }
    base.update(kw)
    return base


def test_translate_query_returns_expected_ask_result() -> None:
    llm = ScriptedFakeLlm(responses=["market_cap_basic > 100000000000 and rsi < 30"])
    result = translate_query("market cap above 10000 Cr and rsi below 30", llm)
    assert isinstance(result, AskResult)
    assert result.filter_text == "market_cap_basic > 100000000000 and rsi < 30"
    assert result.repair_count == 0
    assert len(result.raw_responses) == 1
    assert len(result.filter_group.items) == 2


def test_build_knowledge_pack() -> None:
    pack = build_knowledge_pack()
    assert isinstance(pack, KnowledgePack)
    assert pack.version == "1.0.0"
    assert pack.content_hash
    assert pack.metrics
    assert pack.presets
    assert pack.to_json()


def test_guard_malformed_reply_fails_closed() -> None:
    g = guard_llm_decision({"decision": "maybe"}, BUY)
    assert g.fail_closed
    assert g.effective_intent is None
    assert g.decision.decision is DecisionKind.VETO


def test_guard_non_mapping_reply_fails_closed() -> None:
    g = guard_llm_decision("approve", BUY)  # type: ignore[arg-type]
    assert g.fail_closed
    assert g.effective_intent is None


def test_guard_protective_exit_kept_on_non_approve() -> None:
    g = guard_llm_decision(_raw(decision="veto", decided_quantity=0.0), STOP_SELL)
    assert g.overridden
    assert g.effective_intent == STOP_SELL
    assert any("protective" in r for r in g.reasons)


def test_guard_protective_exit_reduce_only_flag() -> None:
    g = guard_llm_decision(
        _raw(decision="size_down", decided_quantity=10.0), BUY, reduce_only=True
    )
    assert g.overridden
    assert g.effective_intent == BUY


def test_guard_approve_keeps_intent() -> None:
    g = guard_llm_decision(_raw(), BUY)
    assert not g.fail_closed and not g.overridden
    assert g.effective_intent == BUY


def test_guard_size_down_reduces_quantity() -> None:
    g = guard_llm_decision(_raw(decision="size_down", decided_quantity=40.0), BUY)
    assert g.effective_intent is not None
    assert g.effective_intent.quantity == 40.0


def test_guard_quantity_increase_raises_value_error() -> None:
    with pytest.raises(ValueError):
        guard_llm_decision(_raw(decision="size_down", decided_quantity=150.0), BUY)


def test_protective_exit_detection() -> None:
    assert is_protective_exit(STOP_SELL)
    assert is_protective_exit(BUY, reduce_only=True)
    assert not is_protective_exit(BUY)


def test_validate_and_apply_round_trip() -> None:
    decision = validate_llm_decision(_raw(), original_intent=BUY)
    assert decision.decision is DecisionKind.APPROVE
    applied = apply_llm_decision(BUY, decision)
    assert applied == BUY
