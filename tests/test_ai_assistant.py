"""Automated tests for the PawPal AI assistant — guardrails, retrieval, confidence, error handling."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_assistant import PetCareAssistant, _blocked

# ── Minimal fixture knowledge base (no real files needed) ─────────────────────
_FIXTURE_KB = [
    {
        "id": "feeding-dogs-adult",
        "topic": "feeding",
        "text": "Adult dogs generally do best with two meals per day, spaced 8-12 hours apart. "
                "Portion size depends on the dog's weight, breed, and activity level.",
    },
    {
        "id": "cat-toxins-nsaids",
        "topic": "medications",
        "text": "NSAIDs such as ibuprofen and naproxen are toxic to cats and can cause acute "
                "kidney failure even in very small doses. Never give human pain medication to cats.",
    },
    {
        "id": "appetite-loss-dogs",
        "topic": "health",
        "text": "A dog skipping one meal is usually not an emergency. Skipping two or more "
                "consecutive meals warrants a vet call. Appetite loss with lethargy or vomiting "
                "is a red flag.",
    },
]


@pytest.fixture
def assistant(tmp_path):
    """Assistant backed by the fixture KB — no disk I/O to the real knowledge_base/."""
    kb_file = tmp_path / "kb.json"
    kb_file.write_text(json.dumps(_FIXTURE_KB))
    return PetCareAssistant(kb_path=kb_file)


def _mock_api_response(text: str):
    """Build a mock that looks like an anthropic.Anthropic().messages.create() return value."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


# ── Guardrail tests ───────────────────────────────────────────────────────────

def test_blank_query_is_blocked(assistant):
    """Whitespace-only input must be blocked immediately, with zero confidence."""
    result = assistant.answer("   ")
    assert result["blocked"] is True
    assert result["confidence"] == 0.0
    assert result["error"] is None


def test_off_topic_query_is_blocked(assistant):
    """A query with no pet-related vocabulary must be blocked before any API call."""
    result = assistant.answer("What is the best recipe for chocolate cake?")
    assert result["blocked"] is True
    assert result["confidence"] == 0.0


def test_pet_query_passes_guardrail(assistant):
    """A query containing a pet keyword must pass the off-topic guard."""
    with patch("anthropic.Anthropic", return_value=_mock_api_response("Feed twice a day.")):
        result = assistant.answer("How often should I feed my dog?")
    assert result["blocked"] is False


# ── Retrieval tests ───────────────────────────────────────────────────────────

def test_retrieval_finds_relevant_chunk(assistant):
    """Retrieval must return the feeding chunk when asked about dog meal frequency."""
    chunks, _ = assistant.retrieve("How many meals should I give my adult dog per day?")
    chunk_ids = [c.get("id") for c in chunks]
    assert "feeding-dogs-adult" in chunk_ids


def test_confidence_above_threshold_for_direct_match(assistant):
    """A query using terms that directly appear in the KB must score above 0.10."""
    _, confidence = assistant.retrieve("ibuprofen toxic cats kidney failure")
    assert confidence >= 0.10, f"Expected >= 0.10, got {confidence:.3f}"


def test_confidence_near_zero_for_unrelated_query(assistant):
    """A query with no overlapping vocabulary must return near-zero confidence."""
    _, confidence = assistant.retrieve("quantum entanglement photon spin")
    assert confidence < 0.10, f"Expected < 0.10, got {confidence:.3f}"


# ── Error handling tests ──────────────────────────────────────────────────────

def test_api_error_returns_safe_fallback(assistant):
    """If the Claude API raises, the result must include error info and not crash."""
    with patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = Exception("Connection timeout")
        result = assistant.answer("Is ibuprofen safe for cats?")
    assert result["error"] is not None
    assert result["blocked"] is False
    assert isinstance(result["answer"], str) and len(result["answer"]) > 0


def test_result_always_has_required_keys(assistant):
    """Every result — blocked or successful — must contain the full set of required keys."""
    required = {"answer", "confidence", "confidence_label", "sources", "blocked", "error"}

    blocked = assistant.answer("")
    assert required.issubset(blocked.keys()), f"Missing keys in blocked result: {required - blocked.keys()}"

    with patch("anthropic.Anthropic", return_value=_mock_api_response("Walk twice a day.")):
        ok = assistant.answer("How much exercise does my dog need?")
    assert required.issubset(ok.keys()), f"Missing keys in OK result: {required - ok.keys()}"
