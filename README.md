# CancelFill — Intelligent Cancellation Recovery & Waitlist Platform

> **Turn cancelled appointments into recovered revenue.**

---

## 📋 Overview

Appointment-based businesses—such as medical clinics, salons, private tutors, sports facilities, and service centers—lose valuable operational capacity when customers cancel at short notice. Even when other customers are actively waiting for an opening, manually contacting them is slow, inconsistent, and difficult to manage.

**CancelFill** addresses this problem by maintaining an ordered waitlist and managing the automated lifecycle of allocating newly released slots to eligible candidates.

---

## 🎯 The Problem

- **Unused Capacity**: Last-minute cancellations leave valuable time slots empty without sufficient notice to fill them manually.
- **Wasted Demand**: Customers are frequently looking for earlier availability but lack an efficient mechanism to claim newly opened slots.
- **Manual Overhead**: Reaching out to waitlisted clients line-by-line via phone or manual messaging is slow and error-prone.
- **Lost Revenue**: Businesses permanently forfeit revenue from unfulfilled slots that could have been recovered.

---

## 💡 The CancelFill Solution

CancelFill is designed to automatically recover cancelled capacity through a structured workflow:

```
[ Booking Cancelled ]
          │
          ▼
   [ Slot Released ]
          │
          ▼
  [ Waitlist Evaluated ]
          │
          ▼
 [ Candidate Selected ]
          │
          ▼
   [ Temporary Hold ]
          │
          ▼
[ Offer Accepted / Expired ]
          │
  ┌───────┴───────┐
  ▼               ▼
[ Confirmed ]   [ Offer Next Candidate ]
```

---

## ⚡ Why This Is More Than a Simple Waitlist

CancelFill goes beyond basic notification systems ("customer joins waitlist → customer receives alert"). A robust allocation system must handle:

- **Priority Ordering**: Fairly ranking candidates based on request time and rules.
- **Temporary Allocation**: Reserving a slot for a single customer without double-booking.
- **Expiration & Timeouts**: Releasing unclaimed holds when the candidate does not respond within the allocated timeframe.
- **State Management**: Keeping slot, waitlist, hold, and booking statuses strictly synchronized.
- **Competing Requests**: Preventing race conditions when multiple customers or systems interact with the same slot.

---

## 🧠 Core Engineering Challenge — Concurrency & Allocation

Consider a popular sports facility with **20 customers waiting for a single cancelled court slot**:

When the slot opens up:
1. *Who gets priority?*
2. *How long should the selected candidate have to accept the offer?*
3. *What happens if they fail to respond before the offer expires?*
4. *What if two users attempt to claim the slot at almost the exact same millisecond?*
5. *How does the system guarantee that exactly **one** customer receives the confirmed booking?*

These requirements transform CancelFill from a CRUD application into a genuine software engineering challenge involving temporary resource locking, transaction management, and state machine design.

---

## 🔄 State Machine & Slot Lifecycle

### Intended Slot State Machine

```
   [ AVAILABLE ]
        │ (Booking Created)
        ▼
    [ BOOKED ]
        │ (Booking Cancelled)
        ▼
   [ AVAILABLE ]
        │ (Candidate Selected)
        ▼
     [ HELD ] ─────(Hold Expires)────┐
        │                            │
        │ (Offer Accepted)           ▼
        ▼                      [ AVAILABLE ]
   [ CONFIRMED ]
```

*Note: In the planned production system, database transactions (`SELECT ... FOR UPDATE` or optimistic locking) will guarantee atomic state transitions, preventing double-booking during concurrent acceptances.*

---

## ✨ Feature Breakdown

| Feature Category | Feature Description | Status |
| :--- | :--- | :--- |
| **Business** | Create & manage resource time slots | `[Implemented - Review-1]` |
| **Business** | Maintain ordered customer waitlists | `[Implemented - Review-1]` |
| **Business** | Cancel bookings & trigger slot recovery | `[Implemented - Review-1]` |
| **Business** | Recovered revenue & conversion dashboard | `[Planned]` |
| **Customer** | Join slot waitlist with timestamp tracking | `[Implemented - Review-1]` |
| **Customer** | View current waitlist position / status | `[Implemented - Review-1]` |
| **Customer** | Web/Mobile interface to accept or decline slot offers | `[Planned]` |
| **Allocation** | Priority ranking based on earliest join time (`joined_at ASC`) | `[Implemented - Review-1]` |
| **Allocation** | Temporary hold generation (`created_at`, `expires_at`, `status`) | `[Implemented - Review-1]` |
| **Allocation** | Timestamp-based hold expiry evaluation | `[Implemented - Review-1]` |
| **Allocation** | Background scheduler worker for automatic expiry enforcement | `[Planned]` |
| **Allocation** | Automatic cascading offers to next waitlist candidate | `[Planned]` |
| **Concurrency** | Atomic transaction control & race-condition prevention | `[Planned]` |
| **Notifications**| Email, SMS, and Push notification delivery | `[Planned]` |

---

## 📌 Current Review-1 Implementation

For the **Software Engineering Review-1 Evaluation**, the repository demonstrates **four completed core modules**:

1. **PostgreSQL Database Schema**:
   - `slots`: Manages slot resource allocation (`AVAILABLE`, `BOOKED`, `HELD`).
   - `waitlist_entries`: Tracks customer join timestamps (`joined_at`) and statuses (`WAITING`, `OFFERED`, `CANCELLED`, `EXPIRED`).
   - `holds`: Records temporary candidate holds (`created_at`, `expires_at`, `status`).
   - `bookings`: Manages initial bookings for cancellation triggers (`CONFIRMED`, `CANCELLED`).

2. **Core FastAPI Backend Scaffold**:
   - Clean, runnable FastAPI server with Pydantic request/response validation.
   - Endpoints for slot creation (`POST /api/v1/slots`), slot listing (`GET /api/v1/slots`), waitlist registration (`POST /api/v1/waitlist`), and waitlist ordering (`GET /api/v1/slots/{id}/waitlist`).

3. **First-Pass Cancellation → Candidate Selection**:
   - Cancelling a booking (`POST /api/v1/bookings/{id}/cancel`) sets booking status to `CANCELLED` and releases the slot.
   - Evaluates active waitlist entries ordered by `joined_at ASC` (earliest join time = highest priority).
   - Selects the earliest candidate, marks entry as `OFFERED`, creates a temporary hold with a 15-minute expiration, and transitions slot status to `HELD`.

4. **Basic Hold Expiry Prototype**:
   - Timestamp-based evaluation (`POST /api/v1/holds/{id}/check-expiry`) checking `current_time > expires_at`.
   - If expired, transitions `hold.status` to `EXPIRED` and releases `slot.status` back to `AVAILABLE`.
   - *Note: Review-1 uses explicit timestamp evaluation endpoints; background cron workers are part of future sprints.*

---

## 🚀 Planned / Next Sprints

The following components are scheduled for future development phases:

- ⏳ **Atomic Confirmation & Locking**: Database row locking (`SELECT FOR UPDATE`) to handle concurrent acceptances safely.
- ⏳ **Background Scheduler**: Background process (Celery / APScheduler) for periodic hold expiry checks.
- ⏳ **Cascading Offers**: Automatically issuing offers to candidate #2 if candidate #1's hold expires.
- ⏳ **Notification Infrastructure**: Twilio (SMS) / SendGrid (Email) integration for instant offer delivery.
- ⏳ **Frontend Web Interface**: React-based portal for customers and business administrators.
- ⏳ **Business Dashboard**: Analytics tracking recovered slots, conversion rates, and revenue saved.

---

## 🛠️ Software Engineering Focus & SDLC

CancelFill applies core software engineering concepts including state machine design, relational database modeling, RESTful API design, temporary resource allocation, and timestamp evaluation.

### Recommended Incremental SDLC Progression

```
[ Phase 1: Database Schema & Core APIs ] ──▶ (Completed - Review-1)
                   │
                   ▼
[ Phase 2: Waitlist Priority & Cancellation Logic ] ──▶ (Completed - Review-1)
                   │
                   ▼
[ Phase 3: Temporary Hold & Expiry Prototype ] ──▶ (Completed - Review-1)
                   │
                   ▼
[ Phase 4: Atomic Concurrency & Lock Management ] ──▶ (Planned)
                   │
                   ▼
[ Phase 5: Background Scheduler & Cascading Offers ] ──▶ (Planned)
                   │
                   ▼
[ Phase 6: Notifications & User Interface ] ──▶ (Planned)
```

---

## 🏗️ System Architecture & Tech Stack

### High-Level Architecture

```
  Customer Web App / Business Dashboard (Planned)
                        │
                        ▼
             FastAPI Backend (Active)
                        │
                        ▼
            PostgreSQL Database (Active)
```

### Technology Stack

| Domain | Currently Implemented (Review-1) | Planned / Future |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10+, FastAPI, Uvicorn | — |
| **Database & ORM** | PostgreSQL, SQLAlchemy 2.0 | Redis (for caching) |
| **Testing** | Pytest, HTTPX TestClient | End-to-End Cypress |
| **Scheduler** | Timestamp Evaluation Prototype | Celery / APScheduler |
| **Frontend** | Interactive Swagger UI (`/docs`) | React, TailwindCSS |
| **Infrastructure** | Environment Configuration (`.env`) | Docker, Cloud Deployment |

---

## 📁 Repository File Structure

```
CancelFill/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entrypoint & Swagger setup
│   ├── config.py               # Application settings & ENV handling
│   ├── database.py             # SQLAlchemy engine & session setup
│   ├── models.py               # ORM Models: Slot, WaitlistEntry, Hold, Booking
│   ├── schemas.py              # Pydantic validation schemas
│   ├── seed.py                 # Seed dataset generator for Review-1 demo
│   ├── routes/
│   │   ├── slots.py            # POST /slots, GET /slots, GET /slots/{id}
│   │   ├── waitlist.py         # POST /waitlist, GET /slots/{id}/waitlist
│   │   ├── bookings.py         # POST /bookings, GET /bookings
│   │   ├── cancellations.py    # POST /bookings/{id}/cancel (cancellation workflow)
│   │   └── holds.py            # GET /holds, POST /holds/{id}/check-expiry
│   └── services/
│       ├── waitlist_service.py # Join time priority logic (joined_at ASC)
│       ├── cancellation_service.py # Candidate selection & hold trigger
│       └── hold_service.py     # Timestamp-based expiry check logic
├── schema.sql                  # Raw PostgreSQL DDL reference script
├── tests/
│   ├── conftest.py             # Pytest database fixtures (in-memory SQLite StaticPool)
│   ├── test_slots.py           # Slot API unit tests
│   ├── test_waitlist.py        # Waitlist priority & registration tests
│   ├── test_cancellation.py    # Cancellation & candidate selection tests
│   └── test_hold_expiry.py     # Timestamp hold expiry tests
├── .env.example                # Configuration template
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation
```

---

## 💻 Local Setup & Execution Guide

### Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### 1. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

### 4. Seed Development Dataset
Populates 2 slots, 2 waitlist entries (with clear timestamp ordering), and 1 booking ready to cancel:
```bash
python -m app.seed
```

### 5. Run FastAPI Server
```bash
uvicorn app.main:app --reload
```
Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** to interact with Swagger UI.

---

## 🧪 Automated Testing

Execute the test suite covering the four completed modules:
```bash
pytest
```

**Verified Test Suite Output**:
```text
tests/test_cancellation.py .                                             [ 25%]
tests/test_hold_expiry.py .                                              [ 50%]
tests/test_slots.py .                                                    [ 75%]
tests/test_waitlist.py .                                                 [100%]
========================= 4 passed in 0.04s =========================
```

---

## 🎬 Review-1 Live Demonstration Sequence

Follow this step-by-step flow in Swagger UI (`http://127.0.0.1:8000/docs`):

1. **Seed Data**: Run `python -m app.seed` to initialize demo IDs (`slot-demo-1`, `booking-demo-1`).
2. **View Slots**: `GET /api/v1/slots` → Confirm `slot-demo-1` status is `BOOKED`.
3. **Register Waitlist Candidates**:
   - `POST /api/v1/waitlist` for Customer A (earlier timestamp).
   - `POST /api/v1/waitlist` for Customer B (later timestamp).
4. **Inspect Waitlist Priority**: `GET /api/v1/slots/slot-demo-1/waitlist` → Verify Customer A is Priority 1 (`joined_at` earlier) and Customer B is Priority 2.
5. **Demonstrate Cancellation**: `POST /api/v1/bookings/booking-demo-1/cancel`.
   - Verify `booking_status` = `CANCELLED`.
   - Verify candidate `customer_a_alice` is selected.
   - Verify a temporary `hold` is generated with 15-minute `expires_at`.
   - Verify `slot_status` becomes `HELD`.
6. **Evaluate Hold Expiry**: `POST /api/v1/holds/{hold_id}/check-expiry` → Demonstrates timestamp evaluation returning `is_expired: false` and `status: ACTIVE`.

---

> CancelFill transforms cancelled capacity into a structured recovery opportunity — connecting available slots with waiting customers while addressing the real engineering challenges of priority, temporary allocation, expiry, and concurrency.

> **From cancelled slot to recovered booking.**
