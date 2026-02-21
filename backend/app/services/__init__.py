"""
services/__init__.py — Re-exports all service functions for cleaner imports.

Instead of:  from app.services.bet_service import create_bet
You can do:  from app.services import create_bet
"""
from app.services.bet_service import (
    validate_points,
    create_bet,
    get_bet_by_id,
    get_bets_paginated,
    get_public_bets_paginated,
    resolve_bet,
)
from app.services.challenge_service import (
    create_challenge,
    get_challenges_for_bet,
)

# Explicit public API — controls what "from app.services import *" exports
__all__ = [
    "validate_points",
    "create_bet",
    "get_bet_by_id",
    "get_bets_paginated",
    "get_public_bets_paginated",
    "resolve_bet",
    "create_challenge",
    "get_challenges_for_bet",
]
