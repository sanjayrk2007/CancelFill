-- CancelFill - PostgreSQL Database Schema (Review-1)
-- Core tables: slots, waitlist_entries, holds, bookings

DROP TABLE IF EXISTS holds CASCADE;
DROP TABLE IF EXISTS waitlist_entries CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS slots CASCADE;

-- 1. SLOTS
-- Status state machine: AVAILABLE -> BOOKED -> AVAILABLE / HELD
CREATE TABLE slots (
    id VARCHAR(36) PRIMARY KEY,
    resource_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    CONSTRAINT check_slot_status CHECK (status IN ('AVAILABLE', 'BOOKED', 'HELD'))
);

-- 2. WAITLIST_ENTRIES
-- Joined entries ordered by joined_at ASC for priority evaluation
CREATE TABLE waitlist_entries (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'WAITING',
    CONSTRAINT check_waitlist_status CHECK (status IN ('WAITING', 'OFFERED', 'CANCELLED', 'EXPIRED'))
);

-- 3. HOLDS
-- Temporary hold created when candidate is selected post-cancellation
CREATE TABLE holds (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT check_hold_status CHECK (status IN ('ACTIVE', 'EXPIRED', 'RELEASED', 'CONFIRMED'))
);

-- 4. BOOKINGS
-- Minimal booking tracking for demonstrating cancellation workflow
CREATE TABLE bookings (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    booked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CONFIRMED',
    CONSTRAINT check_booking_status CHECK (status IN ('CONFIRMED', 'CANCELLED'))
);

-- Indexes for performance
CREATE INDEX idx_waitlist_slot_joined ON waitlist_entries(slot_id, joined_at ASC);
CREATE INDEX idx_holds_slot ON holds(slot_id);
CREATE INDEX idx_bookings_slot ON bookings(slot_id);
