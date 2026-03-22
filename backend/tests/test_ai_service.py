"""Tests for AI service — all Claude API calls are mocked.
No real API calls are made. No ANTHROPIC_API_KEY required.

Run with: pytest tests/test_ai_service.py -v
"""
import sys
import os
import json
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_service import analyse_account, _build_account_context
from models import AIAnalysis


# ── Fixtures ──────────────────────────────────────────────────────────────────

def base_account(**kwargs):
    defaults = {
        "account_id": "TEST-001",
        "account_name": "Test Corp",
        "priority": "High",
        "risk_score": 65.0,
        "opportunity_score": 35.0,
        "health_score": 48.0,
        "arr_gbp": 150_000,
        "days_to_renewal": 75,
        "contraction_risk_gbp": 20_000,
        "note_sentiment_hint": "Mixed",
        "recent_support_summary": "Some tickets raised.",
        "recent_customer_note": "Sponsor raised concerns.",
        "recent_sales_note": "Renewal at risk.",
        "mrr_trend": -0.08,
        "seat_utilisation": 0.65,
        "latest_nps": 12,
        "avg_csat_90d": 3.8,
        "sla_breaches_90d": 1,
        "urgent_open_tickets_count": 1,
        "null_field_count": 2,
        "confidence": "Medium",
    }
    defaults.update(kwargs)
    return defaults


def valid_claude_response(priority="High") -> str:
    """Return a valid JSON string matching the AIAnalysis schema."""
    return json.dumps({
        "priority": priority,
        "priority_reasoning": (
            f"This account is classified as {priority} due to an MRR decline "
            "of 8% over 3 months and 1 SLA breach in the last 90 days."
        ),
        "top_risks": [
            {"risk": "MRR decline", "evidence": "MRR trend is -8% over 3 months."},
            {"risk": "Renewal at risk", "evidence": "Renewal in 75 days with mixed sentiment."},
        ],
        "top_opportunities": [
            {"opportunity": "Expansion pipeline", "evidence": "Active leads with score > 70."},
        ],
        "recommended_actions": [
            {"action": "Schedule executive sponsor call", "owner": "CSM"},
            {"action": "Present remediation roadmap", "owner": "Leadership"},
            {"action": "Re-qualify expansion pipeline", "owner": "Sales"},
        ],
        "confidence": "Medium",
    })


def mock_claude_response(content: str):
    """Build a mock Anthropic API response object."""
    msg = MagicMock()
    msg.content = [MagicMock()]
    msg.content[0].text = content
    return msg


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAnalyseAccount:

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_valid_response_returns_analysis_object(self, mock_client):
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response(valid_claude_response())
        )
        acc = base_account()
        result = analyse_account(acc)
        assert isinstance(result, AIAnalysis)
        assert result.priority_reasoning != ""
        assert len(result.recommended_actions) == 3
        assert result.error is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_deterministic_priority_enforced_even_if_claude_disagrees(self, mock_client):
        # Claude returns "Low" but deterministic says "Critical"
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response(valid_claude_response(priority="Low"))
        )
        acc = base_account(priority="Critical")
        result = analyse_account(acc)
        assert result.priority == "Critical", (
            f"Deterministic priority should be enforced. "
            f"Got {result.priority}, expected Critical"
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_malformed_json_returns_graceful_error(self, mock_client):
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response("This is definitely not JSON {{ broken")
        )
        acc = base_account()
        result = analyse_account(acc)
        assert isinstance(result, AIAnalysis)
        assert result.error is not None
        assert "parsing" in result.error.lower() or "parse" in result.error.lower()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_empty_response_returns_graceful_error(self, mock_client):
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response("")
        )
        acc = base_account()
        result = analyse_account(acc)
        assert isinstance(result, AIAnalysis)
        assert result.error is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_api_exception_returns_graceful_error(self, mock_client):
        mock_client.return_value.messages.create.side_effect = (
            Exception("Connection refused")
        )
        acc = base_account()
        result = analyse_account(acc)
        assert isinstance(result, AIAnalysis)
        assert result.error is not None
        # Must not crash — must return a valid AIAnalysis with error field set

    def test_no_api_key_returns_unavailable_message(self):
        # Remove API key entirely
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            acc = base_account()
            result = analyse_account(acc)
            assert isinstance(result, AIAnalysis)
            assert "unavailable" in result.priority_reasoning.lower() or \
                   "not configured" in result.priority_reasoning.lower()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_deterministic_priority_appears_in_prompt(self, mock_client):
        """Verify the deterministic priority label is sent to Claude."""
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response(valid_claude_response())
        )
        acc = base_account(priority="Critical")
        analyse_account(acc)

        call_args = mock_client.return_value.messages.create.call_args
        # Find the user message content
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        user_content = " ".join(
            m.get("content", "") for m in messages if m.get("role") == "user"
        )
        assert "Critical" in user_content, (
            "Deterministic priority 'Critical' must appear in the prompt sent to Claude"
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_service._get_client")
    def test_null_notes_trigger_insufficient_data_qualifier(self, mock_client):
        mock_client.return_value.messages.create.return_value = (
            mock_claude_response(valid_claude_response())
        )
        acc = base_account(
            recent_support_summary=None,
            recent_customer_note=None,
            recent_sales_note=None,
        )
        analyse_account(acc)
        call_args = mock_client.return_value.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        user_content = " ".join(
            m.get("content", "") for m in messages if m.get("role") == "user"
        )
        assert "insufficient qualitative data" in user_content.lower() or \
               "null" in user_content.lower(), (
            "Null notes should trigger explicit qualifier in prompt"
        )


class TestBuildAccountContext:

    def test_context_is_valid_json(self):
        acc = base_account()
        ctx = _build_account_context(acc)
        parsed = json.loads(ctx)
        assert isinstance(parsed, dict)

    def test_internal_fields_excluded(self):
        acc = base_account()
        acc["ai_analysis"] = {"some": "cached analysis"}
        acc["decisions"] = [{"id": "d1", "text": "some decision"}]
        ctx = _build_account_context(acc)
        parsed = json.loads(ctx)
        assert "ai_analysis" not in parsed
        assert "decisions" not in parsed

    def test_null_fields_preserved(self):
        acc = base_account(latest_nps=None)
        ctx = _build_account_context(acc)
        parsed = json.loads(ctx)
        assert "latest_nps" in parsed
        assert parsed["latest_nps"] is None
