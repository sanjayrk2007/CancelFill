# CancelFill — Intelligent Cancellation Recovery & Waitlist Platform

> **From cancelled slot to recovered booking.**

CancelFill turns last-minute cancellations into recovered revenue. When a booking is cancelled, the freed slot is automatically offered to the earliest waitlisted customer as a time-limited hold. If they accept, the booking is confirmed. If they decline or the hold expires, the next customer is offered the slot, with no manual calls or messages.

It is built for appointment-based businesses such as clinics, salons, tutors, and sports facilities.

---

## 1. Problem Statement

| Problem | Impact |
| :--- | :--- |
| Late cancellations leave slots empty | Lost revenue and idle capacity |
| Waiting customers don't know a slot opened | Unmet demand |
| Staff contact waitlisted customers by hand | Slow, inconsistent, error-prone |
| Several customers may claim one slot at once | Risk of double-booking |

**Core engineering question:** when 20 customers are waiting for one cancelled slot, how do we guarantee that *exactly one* of them receives the confirmed booking, even if several act in the same millisecond?

---

## 2. Requirements

### Functional
- Business users create and manage time slots and view bookings, waitlists, and recovery statistics.
- Customers browse slots, book, join and leave waitlists, and accept or decline offers.
- Cancelling a booking releases the slot and offers it to the earliest waitlisted customer (`joined_at ASC`).
- Each offer is a temporary hold (default 15 minutes) that expires automatically.
- A declined or expired offer cascades to the next waiting customer.
- Role-based access: `CUSTOMER` and `BUSINESS`.

### Non-Functional
| Quality | Requirement | How it is addressed |
| :--- | :--- | :--- |
| **Correctness** | Never double-book a slot | Row-level locking (`SELECT … FOR UPDATE`) inside transactions |
| **Consistency** | Slot, hold, waitlist, and booking states never contradict each other | Explicit state machine plus invariant tests |
| **Reliability** | Expired holds are always released | Background scheduler with per-hold transactions |
| **Security** | Authenticated, role-restricted access | JWT authentication, bcrypt password hashing, ownership checks |
| **Testability** | Business rules verifiable without a UI | Service layer separated from HTTP layer, injectable clock (`now`) |
| **Maintainability** | Clear separation of concerns | Layered architecture (routes → services → models) |

---

## 3. Solution Overview

```
[ Booking Cancelled ] → [ Slot Released ] → [ Waitlist Evaluated ]
        → [ Candidate Selected ] → [ Temporary Hold ]
        → [ Accepted ]  → [ Confirmed (recovered booking) ]
        → [ Declined / Expired ] → [ Offer next candidate ]
```

### Slot State Machine

```
                 book
  [ AVAILABLE ] ───────────▶ [ BOOKED ]
       ▲  │                      │
       │  │ candidate selected   │ cancel
       │  ▼                      │
       │ [ HELD ] ◀──────────────┘ (via AVAILABLE, then offer)
       │   │   │
       │   │   └── accept ─────▶ [ BOOKED ]  (booking source = RECOVERED)
       └───┴── decline / expire
```

Hold, waitlist entry, and booking each have their own state machine. Allowed transitions are declared in one place, and any illegal transition is rejected.

| Entity | States |
| :--- | :--- |
| Slot | `AVAILABLE`, `BOOKED`, `HELD` |
| Hold | `ACTIVE` → `CONFIRMED` / `EXPIRED` / `DECLINED` |
| Waitlist entry | `WAITING` → `OFFERED` → `CONFIRMED` / `DECLINED` / `EXPIRED` (or `CANCELLED`) |
| Booking | `CONFIRMED` → `CANCELLED` (source: `DIRECT` or `RECOVERED`) |

---

## 4. Architecture

```
  React + Vite frontend (customer & business portals)
                      │  REST / JSON (JWT)
                      ▼
  FastAPI backend ── Routes (HTTP, validation, auth)
                      │
                      ├─ Services (business rules, state machine, allocation)
                      │
                      ├─ APScheduler (hold-expiry job, every 15 s)
                      ▼
  PostgreSQL (transactions, row locks, constraints)
```

| Layer | Responsibility |
| :--- | :--- |
| **Routes** | HTTP contract, request/response schemas, authentication and authorization |
| **Services** | All business rules: allocation, expiry, cascading offers, state transitions |
| **Models** | Persistence and relational constraints |
| **Scheduler** | Periodic enforcement of hold expiry |

### Key Design Decisions

| Decision | Rationale | Trade-off |
| :--- | :--- | :--- |
| Pessimistic locking (`FOR UPDATE`) over optimistic locking | Contention on a single slot is high but short-lived, so waiting is cheaper than retrying | Locks are held for the transaction's duration; needs a real database such as PostgreSQL |
| Centralised state machine | One source of truth for legal transitions | Every new state must be added there |
| Service layer takes an injectable clock | Expiry can be tested without sleeping | Slightly more parameters per function |
| Priority by `joined_at`, tie-broken by ID | Deterministic, explainable fairness | No weighting by customer tier or urgency |
| In-process scheduler | Simple to deploy and run | Not safe for multiple instances without a distributed lock |

---

## 5. Feature Status

| Area | Feature | Status |
| :--- | :--- | :--- |
| Auth | Registration, login, JWT, customer/business roles | Done |
| Business | Create and manage slots | Done |
| Business | Dashboard: slots, bookings, waitlists | Done |
| Business | Recovery statistics (utilization, conversion rate, recovered revenue) | Done |
| Customer | Browse, book, join and leave waitlist | Done |
| Customer | View and accept or decline offers | Done |
| Allocation | Priority ranking by earliest join time | Done |
| Allocation | Temporary holds with expiry | Done |
| Allocation | Automatic expiry via background scheduler | Done |
| Allocation | Cascading offers to the next candidate | Done |
| Concurrency | Atomic acceptance and race-condition prevention | Done |
| Notifications | Email / SMS / push delivery of offers | Planned |
| Scaling | Distributed scheduler lock, caching | Planned |
| Quality | CI pipeline, database migrations | Planned |

---

## 6. Tech Stack

| Domain | Technology |
| :--- | :--- |
| Backend | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| Database / ORM | PostgreSQL 16, SQLAlchemy 2.0 |
| Background jobs | APScheduler |
| Auth | JWT (PyJWT), bcrypt |
| Frontend | React, Vite, Tailwind CSS, Axios |
| Testing | Pytest, HTTPX TestClient |
| Infrastructure | Docker Compose (PostgreSQL) |

---

## 7. Repository Structure

```
CancelFill/
├── app/
│   ├── main.py              # App entrypoint, router wiring, scheduler lifecycle
│   ├── config.py            # Environment-based settings
│   ├── database.py          # Engine and session setup
│   ├── models.py            # ORM models and status enums
│   ├── schemas.py           # Request / response validation
│   ├── security.py          # Password hashing and JWT helpers
│   ├── dependencies.py      # Auth and role dependencies
│   ├── seed.py              # Demo data generator
│   ├── routes/              # auth, slots, bookings, cancellations, waitlist, holds, me, business
│   └── services/
│       ├── state_machine.py     # Legal state transitions
│       ├── allocation_service.py# Booking, cancellation, offers, accept/decline/expire
│       ├── waitlist_service.py  # Waitlist queries
│       ├── hold_service.py      # Hold expiry helpers
│       └── scheduler.py         # Background expiry job
├── frontend/                # React portals for customers and businesses
├── scripts/
│   └── concurrency_demo.py  # Fires N simultaneous accepts at one hold
├── tests/                   # Unit, API, scheduler, and concurrency tests
├── schema.sql               # Reference DDL
├── docker-compose.yml       # PostgreSQL service
├── requirements.txt
└── .env.example
```

---

## 8. Getting Started

### Prerequisites
Python 3.10+, Node.js 18+, Docker.

### Backend
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

docker compose up -d            # PostgreSQL on localhost:5433
cp .env.example .env

python -m app.seed              # optional: demo users, slots, waitlist
uvicorn app.main:app --reload   # API docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev                     # http://localhost:5173
```

### Demo accounts (after seeding)
All passwords are `password123`.

| Role | Email |
| :--- | :--- |
| Business | `dr_smith@example.com` |
| Customer | `alice@example.com`, `bob@example.com`, `charlie@example.com` |

### Configuration (`.env`)
| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL on port 5433 | Database connection |
| `DEFAULT_HOLD_DURATION_SECONDS` | `900` | How long an offer stays open |
| `SCHEDULER_ENABLED` | `true` | Turn automatic expiry on or off |
| `SCHEDULER_INTERVAL_SECONDS` | `15` | How often expiry is checked |
| `JWT_SECRET` | dev placeholder | **Change in any real deployment** |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

---

## 9. Testing & Verification

```bash
# Fast suite (in-memory SQLite): API, allocation, auth, scheduler, reporting
pytest

# Full suite including concurrency tests (requires PostgreSQL)
TEST_DATABASE_URL=postgresql+psycopg2://cancelfill:cancelfill@localhost:5433/cancelfill pytest
```

| Test area | What it verifies |
| :--- | :--- |
| Allocation | Priority order, cascading offers, accept / decline / expire paths |
| State machine | Illegal transitions are rejected |
| Concurrency | Simultaneous accepts, cancels, and expiries leave the system consistent |
| Invariants | After every race: at most one active hold, at most one confirmed booking, never both, and slot status always matches |
| Auth & roles | Unauthorized and cross-owner actions are refused |
| Scheduler | Due holds are expired and the next candidate is offered |

SQLite is used for speed, and the concurrency tests run on PostgreSQL because SQLite does not enforce row-level locks.

### Concurrency demonstration
With the server running:
```bash
python scripts/concurrency_demo.py --n 20
```
Twenty simultaneous accept requests hit one hold. Expected result: **1 success, 19 conflicts (HTTP 409)**.

---

## 10. Demonstration Script

1. **Business** logs in and creates a slot.
2. **Customer A** books it. **Customers B and C** join the waitlist.
3. **Customer A** cancels. B receives an offer with a countdown.
4. **B** declines. The offer cascades to C automatically.
5. **C** accepts. The slot is booked again and the business dashboard shows recovered revenue.
6. Run the concurrency demo to show exactly one winner among simultaneous acceptances.
7. Shorten `DEFAULT_HOLD_DURATION_SECONDS` to show automatic expiry.

---

## 11. Development Process

The project was built incrementally, with each phase delivering working, tested functionality:

| Phase | Deliverable |
| :--- | :--- |
| 1 | Database schema and core APIs |
| 2 | Waitlist priority and cancellation logic |
| 3 | Temporary holds and expiry |
| 4 | Atomic concurrency control and locking |
| 5 | Background scheduler and cascading offers |
| 6 | Authentication, business reporting, and frontend |

---

## 12. Known Limitations & Future Work

- **Notifications:** offers are visible only inside the app. Email and SMS integration is planned.
- **Scheduler scaling:** the in-process scheduler assumes a single instance. Multiple instances would need a distributed lock or a dedicated worker.
- **Fairness model:** priority is strictly first-come, first-served, with no weighting.
- **Schema management:** tables are created on startup, and `schema.sql` is a reference only. Migrations (for example Alembic) are planned.
- **CI/CD:** tests run locally. A CI workflow with a PostgreSQL service container is planned.
- **Security hardening:** token refresh, rate limiting, and secret management are needed before production use.

---

> **CancelFill** turns cancelled capacity into a structured recovery opportunity while solving the real engineering problems of priority, temporary allocation, expiry, and concurrency.
