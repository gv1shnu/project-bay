# Betting Backend API

A Python-based backend API for a betting system with authentication and transaction validation. Built with FastAPI, SQLAlchemy, and JWT authentication.

## Features

- **User Authentication**: JWT-based authentication with secure password hashing
- **User Registration**: New users start with 10 points automatically
- **Bet Management**: Create, view, and update bets with transaction validation
- **Point System**: Automatic point deduction/addition based on bet outcomes
- **Transaction Validation**: Ensures users have sufficient points before placing bets

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **JWT**: JSON Web Tokens for authentication
- **Passlib**: Password hashing with bcrypt
- **Pydantic**: Data validation using Python type annotations
- **SQLite**: Database (easily switchable to PostgreSQL)

## Setup

### 1. Install Dependencies (Python 3.14)

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./betting.db
```

### 3. Seed Sample Data (Optional)

To populate the database with sample bets for showcase purposes:

```bash
python seed_data.py
```

This will create:
- 10 sample users with usernames like `fitness_fanatic`, `bookworm_reader`, `code_master`, etc.
- 20 sample bets with various commitment descriptions
- Each user starts with 100 points
- Default password for all sample users: `password123`

**Note**: 
- The seed script will skip creating bets if bets already exist in the database
- To reset and reseed, delete the `betting.db` file and run the script again
- Sample users can be logged in with their username and password `password123`

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user (starts with 10 points)
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user information

### Bets

- `GET /bets/public` - Get all bets (public, no authentication required)
- `POST /bets/` - Create a new bet (requires authentication)
- `GET /bets/` - Get all bets for current user (requires authentication)
- `GET /bets/{bet_id}` - Get a specific bet (requires authentication)
- `PATCH /bets/{bet_id}` - Update bet status (won/lost/cancelled, requires authentication)

## Usage Examples

### Register a User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

### Create a Bet

```bash
curl -X POST "http://localhost:8000/bets/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5.0,
    "description": "Bet on team A"
  }'
```

### Get User Info

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Bet Validation Rules

1. **Sufficient Points**: Users must have enough points to cover the bet amount
2. **Positive Amount**: Bet amount must be greater than 0
3. **Automatic Deduction**: Points are deducted immediately when a bet is created
4. **Outcome Handling**:
   - **Won**: User receives bet amount × 2 (original + winnings)
   - **Lost**: Points remain deducted (already done at creation)
   - **Cancelled**: Original bet amount is returned to user

## Project Structure

```
bay-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       └── bets.py          # Bet endpoints
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Database

The application uses SQLite by default. The database file (`betting.db`) will be created automatically on first run.

To use PostgreSQL instead, update the `DATABASE_URL` in your `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost/betting_db
```

## Security Notes

- Passwords are hashed using bcrypt
- JWT tokens are used for authentication
- CORS is configured to allow frontend origins (localhost:5173, localhost:3000)
- All endpoints except `/auth/register` and `/auth/login` require authentication

## Integration with Frontend

This backend is integrated with the `bay-frontend` React application. The frontend communicates with this API using:

- **Base URL**: `http://localhost:8000` (default)
- **Authentication**: JWT tokens stored in localStorage
- **CORS**: Configured to allow requests from `http://localhost:5173` (Vite dev server)

### Running with Frontend

1. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the frontend (in a separate terminal):
   ```bash
   npm run dev
   ```

3. The frontend will be available at `http://localhost:5173` and will automatically connect to the backend API.


### Screenshot

![](ss.png)
