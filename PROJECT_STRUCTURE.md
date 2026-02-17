# Project Structure

```
project-bay/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py                # JWT, password hashing, auth dependencies
│   │   ├── config.py              # Configuration & settings
│   │   ├── database.py            # DB engine & session
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging_config.py      # Logging setup
│   │   ├── main.py                # FastAPI app entrypoint
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   ├── seed.py                # Database seeding (demo data on first run)
│   │   ├── routers/               # FastAPI HTTP layer
│   │   │   ├── __init__.py
│   │   │   ├── admin.py           # Admin dashboard endpoints
│   │   │   ├── auth.py            # Authentication endpoints
│   │   │   └── bets/              # Bet management endpoints
│   │   │       ├── __init__.py
│   │   │       ├── bet_crud.py    # Bet CRUD + star operations
│   │   │       ├── challenges.py  # Challenge logic
│   │   │       └── resolution.py  # Bet resolution logic
│   │   ├── services/              # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── bet_service.py     # Bet business logic
│   │   │   └── challenge_service.py # Challenge business logic
│   │   └── utils/                 # Validation utilities
│   │       └── validation.py      # Input & business rule validation
│   ├── initdb/                    # Test Database initialization script
│   │   └── init_test_db.sql
│   ├── tests/                     # Unit & integration tests
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   └── test_bets.py
│   ├── docker-compose.yml         # Docker services configuration
│   ├── requirements.txt           # Python dependencies
│   ├── run.py                     # Application runner
│   └── .env.example               # Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   │   ├── AuthPrompt.tsx     # Sign-in / create account prompt
│   │   │   ├── BetCard.tsx        # Bet display card with star button
│   │   │   ├── ChallengeOverlay.tsx # Challenge interaction overlay
│   │   │   ├── CreateBetModal.tsx  # Bet creation modal
│   │   │   └── ProtectedRoute.tsx # Route protection wrapper
│   │   ├── contexts/              # React context providers
│   │   │   └── AuthContext.tsx    # Global authentication state
│   │   ├── pages/                 # Route-level pages
│   │   │   ├── AdminPage.tsx      # Admin dashboard (users & bets)
│   │   │   ├── HomePage.tsx       # Main feed & bets display
│   │   │   ├── LoginPage.tsx      # Login page
│   │   │   ├── ProfilePage.tsx    # User profile page
│   │   │   └── SignupPage.tsx     # Registration page
│   │   ├── services/              # API clients & frontend business logic
│   │   │   └── api.ts             # API request handlers
│   │   ├── utils/                 # Utility functions
│   │   │   └── avatar.ts          # Avatar generation utilities
│   │   ├── App.tsx                # Root application component
│   │   ├── index.css              # Global styles
│   │   ├── main.tsx               # React entry point
│   │   └── types.ts               # TypeScript type definitions
│   ├── img/                       # Static assets
│   │   └── site.webmanifest       # PWA manifest
│   ├── index.html                 # HTML template
│   ├── package.json               # NPM dependencies & scripts
│   ├── postcss.config.js          # PostCSS configuration
│   ├── tailwind.config.js         # Tailwind CSS configuration
│   ├── tsconfig.json              # TypeScript configuration
│   ├── tsconfig.node.json         # TypeScript node configuration
│   ├── vite.config.ts             # Vite bundler configuration
│   └── .env.example               # Environment variable template
│
├── LICENSE
└── README.md
```

## Layer Responsibilities

| Layer | Directory | Role |
|-------|-----------|------|
| **HTTP** | `routers/` | Request parsing, validation, rate limiting |
| **Business Logic** | `services/` | Point transfers, bet resolution, challenge rules |
| **Data** | `models.py` | ORM definitions, relationships, enums |
| **Validation** | `schemas.py` + `utils/` | Pydantic schemas, regex-based bet validation |
| **UI Components** | `components/` | Reusable React components (BetCard, Modals) |
| **Pages** | `pages/` | Route-level views (Home, Profile, Admin) |
| **State** | `contexts/` | Global auth state via React Context |
| **API Client** | `services/api.ts` | Centralized HTTP calls to backend |
