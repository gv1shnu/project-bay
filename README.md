# Project BAY

Challenging your friends with your web3 wallet on their commitments.

## Setup

### Prerequisites

- Docker desktop
- Python 3.14
- Node.js 18+

### Install Dependencies

```bash
cd frontend
npm install
```

```bash
cd backend
python -m venv venv
source venv/scripts/activate
docker-compose up -d
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=postgresql://bay_user:bay_password@localhost:5432/betting_db
TEST_DATABASE_URL=postgresql://bay_user:bay_password@localhost:5432/betting_test_db
RATELIMIT_ENABLED=True
```

## API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

## Running locally

1. Start the backend server:
   ```bash
   cd backend/
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the frontend (in a separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. The frontend will be available at `http://localhost:5173` and will automatically connect to the backend API at `http://localhost:8000`.


## Future Additions

- [ ] win/loss decision maker
- [ ] sort the feed by likes
- [ ] friends network
- [x] profile page
- [ ] add star button to card
- [x] Search functionality
- [ ] Dark mode
- [x] authentication (login/signup)
- [ ] configuring AI as judge
- [ ] Recommendation system
- [ ] Adding web3 wallet to profile
- [ ] Abuse prevention

