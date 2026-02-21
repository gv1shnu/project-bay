# Project Structure

```
project-bay/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py                  # JWT, password hashing, auth dependencies
│   │   ├── cache.py                 # In-memory feed cache (invalidated on new bet)
│   │   ├── config.py                # Settings loaded from .env (DB, JWT, Groq key, etc.)
│   │   ├── database.py              # DB engine, SessionLocal, Base, get_db dependency
│   │   ├── deadline_checker.py      # Background scheduler — auto-resolves expired bets
│   │   ├── exceptions.py            # Custom HTTP exceptions (BetNotFound, etc.)
│   │   ├── logging_config.py        # Structured logging setup
│   │   ├── main.py                  # FastAPI app entrypoint, router registration, startup
│   │   ├── models.py                # SQLAlchemy ORM models & enums (see DB section below)
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── routers/                 # HTTP layer — thin, delegates to services
│   │   │   ├── __init__.py
│   │   │   ├── admin.py             # Admin dashboard endpoints
│   │   │   ├── auth.py              # Register, login, /me
│   │   │   ├── notifications.py     # Notification list & mark-read endpoints
│   │   │   └── bets/
│   │   │       ├── __init__.py
│   │   │       ├── bet_crud.py      # Bet CRUD, feed, star, proof upload + LLM queue trigger
│   │   │       ├── challenges.py    # Challenge stake, list, withdraw
│   │   │       └── resolution.py   # Bet resolution PATCH (won / lost / cancelled)
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── bet_service.py       # Bet creation, pagination, resolve (payouts)
│   │   │   └── challenge_service.py # Challenge creation, withdrawal logic
│   │   └── utils/                   # Utility layer
│   │       ├── validation.py        # Regex-based personal commitment check (is_personal)
│   │       └── llm_validator.py     # LangGraph + Groq async bet quality validator
│   ├── tests/
│   │   ├── conftest.py              # Pytest fixtures (DB, test client, token factory)
│   │   ├── test_auth.py             # Auth endpoint tests
│   │   ├── test_bets.py             # Bet CRUD tests
│   │   ├── test_betting_flow.py     # End-to-end betting flow (win/lose/cancel)
│   │   └── test_llm_validator.py    # LangGraph validator unit tests
│   ├── test_helper.py               # Manual API script for debugging point math
│   ├── docker-compose.yml           # Postgres + test DB services
│   ├── requirements.txt             # Python dependencies (prod)
│   ├── run.py                       # Application runner
│   └── .env.example                 # Environment variable template
│
├── frontend/
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   │   ├── AuthPrompt.tsx       # Sign-in / create account nudge
│   │   │   ├── BetCard.tsx          # Feed card with star button + status badge
│   │   │   ├── BetDetailModal.tsx   # Full bet details overlay
│   │   │   ├── ChallengeOverlay.tsx # Challenge creation interaction
│   │   │   ├── CreateBetModal.tsx   # Bet creation form modal
│   │   │   ├── ProofUploadModal.tsx # Proof submission modal (media + comment)
│   │   │   └── ProtectedRoute.tsx   # Route guard wrapper
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx      # Global auth state (user, token, login/logout)
│   │   ├── pages/
│   │   │   ├── AdminPage.tsx        # Admin dashboard (all users & bets)
│   │   │   ├── HomePage.tsx         # Main feed with search & filters
│   │   │   ├── LoginPage.tsx        # Login form
│   │   │   ├── NotificationsPage.tsx # Notification inbox
│   │   │   ├── ProfilePage.tsx      # User profile, win/loss badges, withdrawal
│   │   │   ├── ProofReviewPage.tsx  # Challenger proof review & voting
│   │   │   └── SignupPage.tsx       # Registration form
│   │   ├── services/
│   │   │   └── api.ts               # Centralized axios HTTP calls to backend
│   │   ├── utils/
│   │   │   └── avatar.ts            # Avatar / initials generation
│   │   ├── App.tsx                  # Root component & routing
│   │   ├── index.css                # Global styles
│   │   ├── main.tsx                 # React entry point
│   │   └── types.ts                 # TypeScript interfaces for all API models
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── .env.example
│
├── IN_MY_OWN_WORDS.md               # Product spec & philosophy
├── PROJECT_STRUCTURE.md             # This file
├── LICENSE
└── README.md
```

---

## Database Schema

All tables are managed by SQLAlchemy and auto-created at startup via `Base.metadata.create_all`.

```
┌──────────────────────────────────────────────────────────────┐
│  users                                                       │
│  id · username · email · hashed_password · points           │
│  created_at · updated_at                                     │
└───────────┬──────────────────────────────┬───────────────────┘
            │ 1:N                          │ 1:N
            ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│  bets                     │   │  notifications               │
│  id · user_id (FK)        │   │  id · user_id (FK)          │
│  title · criteria         │   │  bet_id (FK, nullable)      │
│  amount · deadline        │   │  message · is_read          │
│  status (BetStatus enum)  │   └─────────────────────────────┘
│  stars                    │
│  proof_comment            │
│  proof_media_url          │
│  proof_submitted_at       │          Enums
│  proof_deadline           │  ─────────────────────────────
│  created_at · updated_at  │  BetStatus:
└──────┬────────────────────┘    active | pending | won
       │                          lost  | cancelled
       │ 1:N              ─────────────────────────────
       ▼                  ChallengeStatus:
┌──────────────────────────────┐  pending | won | lost | withdrew
│  challenges                  │
│  id · bet_id (FK)            │  ─────────────────────────────
│  challenger_id (FK→users)    │  QueueStatus:
│  amount                      │    pending | processing
│  status (ChallengeStatus)    │    completed | failed
│  created_at                  │
└──────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  proof_votes                                                 │
│  id · bet_id (FK) · user_id (FK) · vote · created_at        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  bet_stars  (unique: bet_id + user_id)                       │
│  id · bet_id (FK) · user_id (FK) · created_at               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  bet_validation_queue  (unique: bet_id)                      │
│  id · bet_id (FK)                                            │
│  status (QueueStatus) · is_valid · result_raw · attempts     │
│  created_at · updated_at                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

| Layer | Directory / File | Role |
|---|---|---|
| **HTTP** | `routers/` | Request parsing, auth injection, thin delegation to services |
| **Business Logic** | `services/` | Point transfers, bet resolution, challenge rules |
| **Data** | `models.py` | ORM table definitions, relationships, enums |
| **Validation** | `schemas.py` + `utils/validation.py` | Pydantic schemas, regex personal-commitment check |
| **LLM Check** | `utils/llm_validator.py` | LangGraph state machine → Groq API → cancel invalid bets |
| **Background Jobs** | `deadline_checker.py` | Cron ticker — auto-resolves expired & ignored-proof bets |
| **UI Components** | `frontend/components/` | Reusable React components (cards, modals) |
| **Pages** | `frontend/pages/` | Route-level views (Home, Profile, Admin, Notifications) |
| **State** | `contexts/` | Global auth state via React Context |
| **API Client** | `services/api.ts` | Centralized HTTP calls to backend |
