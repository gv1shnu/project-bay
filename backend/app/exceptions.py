"""
exceptions.py — Custom exception classes for the betting API.

All custom exceptions inherit from BettingAPIException, which is caught
by a global handler in main.py and returned as a clean JSON error response.

This pattern keeps error handling consistent across all endpoints.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse


class BettingAPIException(Exception):
    """Base exception for all betting API errors. Subclass this for specific errors."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientFundsError(BettingAPIException):
    """Raised when user tries to stake more points than they have."""
    
    def __init__(self, available: float, required: float):
        self.available = available
        self.required = required
        message = f"Insufficient points. You have {available} points, but need {required}"
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class BetNotFoundError(BettingAPIException):
    """Raised when a bet ID doesn't exist in the database."""
    
    def __init__(self, bet_id: int):
        self.bet_id = bet_id
        message = f"Bet with id {bet_id} not found"
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class UserAlreadyExistsError(BettingAPIException):
    """Raised when registering with a username or email that's already taken."""
    
    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        message = f"{field.capitalize()} '{value}' already exists"
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class InvalidCredentialsError(BettingAPIException):
    """Raised on failed login attempt — wrong username or password."""
    
    def __init__(self):
        message = "Incorrect username or password"
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidBetAmountError(BettingAPIException):
    """Raised when bet amount is zero or negative."""
    
    def __init__(self, amount: float):
        self.amount = amount
        message = "Bet amount must be greater than 0"
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


async def betting_api_exception_handler(request: Request, exc: BettingAPIException) -> JSONResponse:
    """
    Global exception handler registered in main.py.
    Catches any BettingAPIException and returns a uniform JSON error response:
      {"detail": "error message here"}
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
