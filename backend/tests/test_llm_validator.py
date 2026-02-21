import pytest
from app.utils.llm_validator import validate_bet_with_llm

def test_validate_bet_with_llm_valid_personal_commitment():
    """
    Test that a valid personal commitment is accepted by the LLM.
    We test a clear, measurable personal goal.
    """
    result = validate_bet_with_llm(
        title="I will read 20 pages of a book every day for a week",
        criteria="Daily updates with picture of the page I'm on.",
        amount=10
    )
    
    # Assert LLM parsed the instruction correctly
    assert result["is_valid"] is True
    assert "reason" in result
    assert len(result["reason"]) <= 50 # Respecting the prompt constraint


def test_validate_bet_with_llm_invalid_prediction():
    """
    Test that an external prediction (sports, stocks) is rejected.
    """
    result = validate_bet_with_llm(
        title="Bitcoin will hit 100k by tomorrow",
        criteria="Check Binance price at noon",
        amount=50
    )
    
    assert result["is_valid"] is False
    assert "reason" in result


def test_validate_bet_with_llm_invalid_vague():
    """
    Test that a vague unmeasurable goal might be rejected.
    """
    result = validate_bet_with_llm(
        title="I will be a better person",
        criteria="Just trust me bro",
        amount=5
    )
    
    # LLM usually rejects this for lack of measurable criteria
    assert result["is_valid"] is False
    assert "reason" in result


def test_validate_bet_with_llm_invalid_abuse():
    """
    Test that malicious/abusive bets are rejected by rule 4.
    """
    result = validate_bet_with_llm(
        title="I will bully someone on Twitter",
        criteria="Post 5 mean tweets today",
        amount=10
    )
    
    assert result["is_valid"] is False
    assert "reason" in result


def test_validate_bet_with_llm_invalid_static_post():
    """
    Test that passive non-actionable bets are rejected by rule 1.
    """
    result = validate_bet_with_llm(
        title="I will be happy today",
        criteria="I will smile",
        amount=2
    )

    assert result["is_valid"] is False
    assert "reason" in result
