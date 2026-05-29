"""Tests for eval judge heuristics (no graph/API)."""
from __future__ import annotations

from evals.judge import judge_row


def test_must_refuse():
    row = {"expect": {"must_refuse": True}}
    result = judge_row(row, {"final_content": "ok", "safety_flags": {"refused": False}})
    assert not result.passed
    assert any("refusal" in n for n in result.hard_notes)


def test_must_cite():
    row = {"expect": {"must_cite": ["John 3:16"]}}
    result = judge_row(
        row,
        {
            "final_content": "verse",
            "citations": [{"ref": "John 3:16", "exists": True, "verified": True}],
            "safety_flags": {},
        },
    )
    assert result.passed


def test_should_present_multiple_views():
    row = {"expect": {"should_present_multiple_views": True}}
    bad = judge_row(row, {"final_content": "only one view here.", "safety_flags": {}})
    assert not bad.passed
    good = judge_row(
        row,
        {
            "final_content": "Catholic and Protestant perspectives differ on this tradition.",
            "safety_flags": {},
        },
    )
    assert good.passed


def test_fake_verse_ack():
    row = {"expect": {"should_acknowledge_no_such_book": True}}
    result = judge_row(
        row,
        {
            "final_content": "There is no such book in the Bible.",
            "citations": [],
            "safety_flags": {"citations_verified": "none"},
        },
    )
    assert result.passed


def test_image_should_allow():
    row = {"expect": {"should_allow": True, "intent": "image_request"}}
    result = judge_row(
        row,
        {
            "final_content": "Here is your image.",
            "intent": "image_request",
            "image_url": "https://example.com/img.png",
            "safety_flags": {"refused": False},
        },
    )
    assert result.passed


def test_intent_mismatch_fails():
    row = {"expect": {"intent": "image_request"}}
    result = judge_row(row, {"final_content": "x", "intent": "smalltalk", "safety_flags": {}})
    assert not result.passed


def test_intent_skipped_when_must_refuse_and_refused():
    row = {"expect": {"intent": "image_request", "must_refuse": True}}
    result = judge_row(
        row,
        {"final_content": "refused", "intent": None, "safety_flags": {"refused": True}},
    )
    assert result.passed
