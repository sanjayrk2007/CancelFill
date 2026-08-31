# CancelFill – Intelligent Cancellation Recovery & Waitlist Platform

> **Software Engineering Review-1 Presentation Repository**

---

## 1. Current Review-1 Implementation

For the **Review-1 Presentation**, only the following four core modules are implemented:

1. **PostgreSQL Database Schema**:
   - `slots`: Manages resource slot availability (`AVAILABLE`, `BOOKED`, `HELD`).
   - `waitlist_entries`: Tracks customer waitlist join timestamps (`joined_at`) and statuses (`WAITING`, `OFFERED`, `CANCELLED`, `EXPIRED`).
   - `holds`: Stores temporary holds generated for selected candidates (`created_at`, `expires_at`, `status`).
   - `bookings`: Minimal booking management to demonstrate the cancellation trigger (`CONFIRMED`, `CANCELLED`).

2. **Core FastAPI Backend Scaffold**:
   - Runnable FastAPI application with modular routes and Pydantic validation schemas.
   - Basic endpoints for slot creation (`POST /api/v1/slots`), slot viewing (`GET /api/v1/slots`), waitlist registration (`POST /api/v1/waitlist`), and waitlist viewing (`GET /api/v1/slots/{id}/waitlist`).

3. **First-Pass Cancellation → Candidate Selection**:
   - Cancellation endpoint (`POST /api/v1/bookings/{booking_id}/cancel`) marks booking as `CANCELLED` and releases slot.
   - Evaluates active waitlist entries for the slot ordered by `joined_at ASC` (earliest join time = highest priority).
   - Automatically selects the earliest eligible candidate, marks their waitlist entry as `OFFERED`, creates a temporary hold, and sets slot status to `HELD`.

4. **Basic Hold Expiry Prototype**:
   - Timestamp-based expiry check (`POST /api/v1/holds/{hold_id}/check-expiry`) evaluating `current_time > expires_at`.
   - If expired, updates `hold.status = EXPIRED` and releases the slot (`slot.status = AVAILABLE`).

---

## 2. System Architecture & Workflow

```
Customer / Business User
          │
          ▼
   FastAPI Backend
          │
          ▼
 PostgreSQL Database
```

### Cancellation & Candidate Selection Flow

```
[ Booking Cancelled ]
          │
          ▼
[ Slot Marked AVAILABLE ]
          │
          ▼
[ Query Waitlist (ORDER BY joined_at ASC) ]
          │
          ▼
[ Select Earliest Candidate ]
          │
          ▼
[ Mark Waitlist Entry as OFFERED ]
          │
          ▼
[ Create Temporary Hold (created_at, expires_at) ]
          │
          ▼
[ Slot Status = HELD ]
          │
          ▼
[ Timestamp Expiry Check (is_expired = now > expires_at) ]
```

---

## 3. Future Work / Intentionally Not Implemented

The following features belong to future sprints and are **NOT** implemented in this Review-1 scope:

- ❌ **Atomic Concurrency / Locking**: Row-level locking (`SELECT ... FOR UPDATE`), optimistic locking, or race-condition protection.
- ❌ **Background Scheduler**: Celery, APScheduler, cron jobs, or automatic periodic background polling.
- ❌ **Automatic Cascading Offers**: Automatic escalation to the next waitlist candidate upon expiry.
- ❌ **Notifications**: Email, SMS, or Push notifications.
- ❌ **Frontend UI**: Customer-facing React interface or business dashboard.
- ❌ **Analytics**: Revenue recovery analytics or predictive scoring.

---

## 4. Running the Project Locally

### Prerequisites
- Python 3.10+
- (Optional) PostgreSQL database instance. *Note: The application defaults to PostgreSQL schema semantics; for quick local testing without a live PostgreSQL server, SQLite engine fallback is automatically supported.*

### Step 1: Clone & Navigate
```bash
cd CancelFill
```

### Step 2: Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### Step 5: Seed Development Dataset
Run the seed script to clear existing data and populate a small demo dataset (2 slots, 2 waitlist entries, 1 booking):
```bash
python -m app.seed
```

### Step 6: Start FastAPI Server
```bash
uvicorn app.main:app --reload
```
The server will run at `http://127.0.0.1:8000`.

---

## 5. Review-1 Presentation & Live Demo Sequence

Follow this step-by-step sequence in **Swagger UI** (`http://127.0.0.1:8000/docs`):

1. **Open Swagger UI**: Navigate to `http://127.0.0.1:8000/docs`.
2. **Seed Data (or Create New Slot)**:
   - Execute `python -m app.seed` in your terminal. Note the printed IDs (`slot-demo-1`, `booking-demo-1`).
3. **View Slots**:
   - `GET /api/v1/slots`
   - Observe `slot-demo-1` status is `BOOKED`.
4. **Register Customer A on Waitlist**:
   - `POST /api/v1/waitlist`
   - Body: `{"slot_id": "slot-demo-2", "user_id": "customer_a", "joined_at": "2026-09-01T10:00:00Z"}`
5. **Register Customer B on Waitlist**:
   - `POST /api/v1/waitlist`
   - Body: `{"slot_id": "slot-demo-2", "user_id": "customer_b", "joined_at": "2026-09-01T10:05:00Z"}`
6. **View Waitlist Priority**:
   - `GET /api/v1/slots/slot-demo-1/waitlist`
   - Observe that `customer_a_alice` is Priority 1 (`joined_at` earlier) and `customer_b_bob` is Priority 2.
7. **Demonstrate Cancellation**:
   - `POST /api/v1/bookings/booking-demo-1/cancel`
   - Observe response:
     - `booking_status`: `CANCELLED`
     - `candidate_selected`: `true`
     - `selected_user_id`: `customer_a_alice`
     - `slot_status`: `HELD`
     - `hold`: Active temporary hold created with 15-minute `expires_at` timestamp.
8. **Demonstrate Hold Expiry Check**:
   - Copy the `hold.id` from the cancellation response.
   - `POST /api/v1/holds/{hold_id}/check-expiry`
   - Shows timestamp evaluation result (`is_expired`, `status`, `expires_at`).

---

## 6. Running Automated Tests

Run the pytest suite covering all 4 modules:
```bash
pytest
```
Expected output: 4 passed test suites (`test_slots.py`, `test_waitlist.py`, `test_cancellation.py`, `test_hold_expiry.py`).
