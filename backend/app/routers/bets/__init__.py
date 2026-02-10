"""
routers/bets/__init__.py — Assembles all bet-related sub-routers into one.

All endpoints are prefixed with /bets and tagged for OpenAPI docs.
Sub-routers:
  - bet_crud: create, list, get bets
  - challenges: create, list, accept, reject challenges
  - resolution: resolve bet outcomes (won/lost/cancelled)
"""
from fastapi import APIRouter
from app.routers.bets.bet_crud import router as bet_crud_router
from app.routers.bets.challenges import router as challenges_router
from app.routers.bets.resolution import router as resolution_router

# Parent router — all sub-routers inherit the /bets prefix
router = APIRouter(prefix="/bets", tags=["bets"])

# Include all sub-routers (their endpoints merge into this parent)
router.include_router(bet_crud_router)
router.include_router(challenges_router)
router.include_router(resolution_router)
