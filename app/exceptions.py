"""
Custom exception classes and global exception handlers for the betting API.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse


class BettingAPIException(Exception):
    """Base exception for the betting API."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientFundsError(BettingAPIException):
    """Raised when user has insufficient points for a transaction."""
    
    def __init__(self, available: float, required: float):
        self.available = available
        self.required = required
        message = f"Insufficient points. You have {available} points, but need {required}"
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class BetNotFoundError(BettingAPIException):
    """Raised when a bet is not found."""
    
    def __init__(self, bet_id: int):
        self.bet_id = bet_id
        message = f"Bet with id {bet_id} not found"
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class UserAlreadyExistsError(BettingAPIException):
    """Raised when trying to register with an existing username or email."""
    
    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        message = f"{field.capitalize()} '{value}' already exists"
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class InvalidCredentialsError(BettingAPIException):
    """Raised when login credentials are invalid."""
    
    def __init__(self):
        message = "Incorrect username or password"
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidBetAmountError(BettingAPIException):
    """Raised when bet amount is invalid."""
    
    def __init__(self, amount: float):
        self.amount = amount
        message = "Bet amount must be greater than 0"
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


async def betting_api_exception_handler(request: Request, exc: BettingAPIException) -> JSONResponse:
    """Global exception handler for BettingAPIException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
