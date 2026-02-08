"""Bets router package - combines all bet-related endpoints."""
from fastapi import APIRouter
from app.routers.bets.bet_crud import router as bet_crud_router
from app.routers.bets.challenges import router as challenges_router
from app.routers.bets.resolution import router as resolution_router

router = APIRouter(prefix="/bets", tags=["bets"])

# Include all sub-routers
router.include_router(bet_crud_router)
router.include_router(challenges_router)
router.include_router(resolution_router)
