# Project BAY — Flowchart

## System Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite)"]
        UI["UI Components<br/>BetCard, AuthPrompt, Modals"]
        Pages["Pages<br/>Home, Profile, Admin, Login, Signup"]
        AuthCtx["AuthContext<br/>JWT Token Management"]
        API["API Service<br/>api.ts"]
    end

    subgraph Backend["Backend (FastAPI)"]
        Routers["Routers<br/>auth, bets, admin"]
        Services["Services<br/>bet_service, challenge_service"]
        Auth["Auth Module<br/>JWT + bcrypt"]
        Models["Models<br/>User, Bet, Challenge"]
        Seed["Seed<br/>Demo Data"]
    end

    subgraph Database["PostgreSQL (Docker)"]
        Users["users"]
        Bets["bets"]
        Challenges["challenges"]
    end

    Pages --> UI
    Pages --> AuthCtx
    Pages --> API
    API -->|HTTP REST| Routers
    Routers --> Auth
    Routers --> Services
    Services --> Models
    Models --> Users
    Models --> Bets
    Models --> Challenges
    Seed -->|First Run| Models
```

---

## User Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant DB as PostgreSQL

    User->>FE: Enter credentials
    FE->>API: POST /auth/login
    API->>DB: Query user by username
    DB-->>API: User record
    API->>API: Verify bcrypt hash
    API-->>FE: JWT access token
    FE->>FE: Store token in AuthContext
    FE-->>User: Redirect to Home
```

---

## Bet Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Active: User creates bet<br/>(points deducted)

    Active --> Active: Receives challenges
    Active --> Won: Creator marks won<br/>(gets own stake + challenger stakes)
    Active --> Lost: Creator marks lost<br/>(challengers get 2x their stakes)
    Active --> Cancelled: Creator cancels<br/>(everyone refunded)

    Won --> [*]
    Lost --> [*]
    Cancelled --> [*]
```

---

## Challenge Flow

```mermaid
sequenceDiagram
    actor Challenger
    actor Creator
    participant API as FastAPI
    participant DB as PostgreSQL

    Challenger->>API: POST /bets/{id}/challenge
    API->>DB: Deduct challenger's points
    API->>DB: Create challenge (PENDING)
    API-->>Challenger: Challenge created

    Creator->>API: POST /challenges/{id}/accept
    API->>DB: Update challenge → ACCEPTED
    API->>DB: Increase bet's matched stake
    API-->>Creator: Challenge accepted

    Note over Creator,DB: OR

    Creator->>API: POST /challenges/{id}/reject
    API->>DB: Update challenge → REJECTED
    API->>DB: Refund challenger's points
    API-->>Creator: Challenge rejected
```

---

## Bet Resolution & Point Distribution

```mermaid
flowchart TD
    A["Creator resolves bet"] --> B{Status?}

    B -->|WON| C["Creator gets:<br/>own stake + all challenger stakes"]
    B -->|LOST| D["Each accepted challenger gets:<br/>2× their stake"]
    B -->|CANCELLED| E["Full refund to everyone:<br/>creator + all non-rejected challengers"]

    C --> F["Bet closed"]
    D --> F
    E --> F
```

---

## Star & Feed System

```mermaid
flowchart LR
    A["User clicks ⭐"] --> B["POST /bets/{id}/star"]
    B --> C["Increment stars in DB"]
    C --> D["Return updated count"]

    E["HomePage loads"] --> F["GET /bets/public"]
    F --> G["Query: ORDER BY stars DESC, created_at DESC"]
    G --> H["Feed sorted by popularity"]

    I["Auto-refresh every 30s"] --> F
```

---

## Request Flow (Full Stack)

```mermaid
flowchart LR
    subgraph Client
        A["React App"]
    end

    subgraph Server
        B["Rate Limiter<br/>(slowapi)"]
        C["Router<br/>(endpoint)"]
        D["Auth<br/>(JWT decode)"]
        E["Service<br/>(business logic)"]
        F["SQLAlchemy<br/>(ORM)"]
    end

    subgraph DB
        G["PostgreSQL"]
    end

    A -->|"HTTP + JWT"| B --> C --> D --> E --> F --> G
    G -->|Response| F --> E --> C --> A
```
