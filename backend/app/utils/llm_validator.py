import json
import logging
from typing import TypedDict, Annotated, Dict, Any
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from app.models import Bet, BetValidationQueue, QueueStatus, BetStatus, User
from app.config import settings
from app.services.bet_service import resolve_bet
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# --- LangGraph Setup ---

class AgentState(TypedDict):
    bet_title: str
    bet_criteria: str
    amount: int
    is_valid: bool
    reason: str
    raw_response: str
    error: str

# Instantiate the LLM using Groq
# We require JSON mode to ensure structured output
llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.0
).bind(response_format={"type": "json_object"})


SYS_PROMPT = """You are an automated moderator for a betting platform. 
Your job is to determine if a bet is a legitimate, actionable, personal, and measurable commitment.

A valid bet MUST:
1. Be a personal, actionable commitment by the user themselves (e.g. "I will read 10 pages", "I will run 5km"). Static/passive posts that don't promote active effort (e.g. "I will wear make up today", "I will be happy") are NOT allowed.
2. NOT be a prediction about external events they do not control (e.g. "Team A will win the Superbowl", "Bitcoin will hit 100k").
3. Have clear, measurable criteria for success or failure.
4. STRICT MODERATION: Immediately REJECT (is_valid: false) any content containing NSFW themes, self-harm, abuse, hate speech, or dark subject matter. The platform is strictly for competitive, positive growth.

Analyze the provided 'title' and 'criteria'.

You MUST output ONLY valid JSON in the following format:
{
  "is_valid": true,
  "reason": "Explain your reasoning here in 50 characters max."
}
"""

def evaluate_bet_node(state: AgentState) -> dict:
    prompt = f"Title: {state['bet_title']}\nCriteria: {state['bet_criteria']}\nAmount: {state['amount']}"
    messages = [
        SystemMessage(content=SYS_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON
        parsed = json.loads(content)
        return {
            "raw_response": content,
            "is_valid": bool(parsed.get("is_valid", False)),
            "reason": parsed.get("reason", "No reason provided")
        }
    except Exception as e:
        logger.error(f"LLM Evaluation failed: {e}")
        return {
            "error": str(e),
            "is_valid": False
        }

# Build Graph
builder = StateGraph(AgentState)
builder.add_node("evaluate", evaluate_bet_node)
builder.add_edge(START, "evaluate")
builder.add_edge("evaluate", END)
validator_graph = builder.compile()


def validate_bet_with_llm(title: str, criteria: str, amount: int) -> dict:
    """Wrapper to run the graph on a single bet."""
    initial_state = {
        "bet_title": title,
        "bet_criteria": criteria,
        "amount": amount,
        "is_valid": False,
        "reason": "",
        "raw_response": "",
        "error": ""
    }
    result = validator_graph.invoke(initial_state)
    return result


def process_validation_queue():
    """
    Fetches pending items from BetValidationQueue, evaluates them,
    and cancels invalid bets.
    To be run as a background task.
    """
    logger.info("Starting process_validation_queue...")
    db: Session = SessionLocal()
    try:
        # Fetch pending items (or failed items with < 3 attempts)
        queue_items = db.query(BetValidationQueue).filter(
            (BetValidationQueue.status == QueueStatus.PENDING) | 
            ((BetValidationQueue.status == QueueStatus.FAILED) & (BetValidationQueue.attempts < 3))
        ).all()
        
        if not queue_items:
            logger.info("No pending bets in queue.")
            return

        # Mark as processing
        for item in queue_items:
            item.status = QueueStatus.PROCESSING
        db.commit()
        
        for item in queue_items:
            item.attempts += 1
            bet = item.bet
            
            if not bet or bet.status != BetStatus.ACTIVE:
                # Bet is cancelled or no longer active, skip
                item.status = QueueStatus.COMPLETED
                item.result_raw = "Bet no longer active"
                db.commit()
                continue

            logger.info(f"Validating bet {bet.id}: {bet.title}")
            
            # Run graph
            result = validate_bet_with_llm(bet.title, bet.criteria, bet.amount)
            
            if result.get("error"):
                # If error, mark failed, will retry if attempts < 3
                item.status = QueueStatus.FAILED if item.attempts >= 3 else QueueStatus.PENDING
                item.result_raw = result["error"]
                logger.error(f"Validation error for bet {bet.id}: {result['error']}")
            else:
                item.status = QueueStatus.COMPLETED
                item.is_valid = 1 if result["is_valid"] else 0
                item.result_raw = result["raw_response"]
                
                if not result["is_valid"]:
                    logger.warning(f"Bet {bet.id} deemed INVALID by LLM: {result['reason']}. Cancelling...")
                    try:
                        # Cancel the bet. `resolve_bet` expects the bet creator to make the cancellation,
                        # but since this is an automated system task, we impersonate the creator.
                        creator = db.query(User).filter(User.id == bet.user_id).first()
                        resolve_bet(db, creator, bet.id, BetStatus.CANCELLED)
                    except Exception as e:
                        logger.error(f"Failed to cancel invalid bet {bet.id}: {e}")
                        # Revert queue status to try cancelling again later maybe
                        item.status = QueueStatus.FAILED
                else:
                    logger.info(f"Bet {bet.id} deemed VALID by LLM.")
                    
            db.commit()

        logger.info("Finished process_validation_queue.")
    finally:
        db.close()
