-- CancelFill - PostgreSQL Database Schema
-- Core tables: users, slots, waitlist_entries, holds, bookings

DROP TABLE IF EXISTS holds CASCADE;
DROP TABLE IF EXISTS waitlist_entries CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS slots CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. USERS
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT check_user_role CHECK (role IN ('CUSTOMER', 'BUSINESS'))
);

-- 2. SLOTS
CREATE TABLE slots (
    id VARCHAR(36) PRIMARY KEY,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    CONSTRAINT check_slot_status CHECK (status IN ('AVAILABLE', 'BOOKED', 'HELD'))
);

-- 3. WAITLIST_ENTRIES
CREATE TABLE waitlist_entries (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'WAITING',
    CONSTRAINT check_waitlist_status CHECK (status IN ('WAITING', 'OFFERED', 'CANCELLED', 'EXPIRED'))
);

-- 4. HOLDS
CREATE TABLE holds (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT check_hold_status CHECK (status IN ('ACTIVE', 'EXPIRED', 'RELEASED', 'CONFIRMED'))
);

-- 5. BOOKINGS
CREATE TABLE bookings (
    id VARCHAR(36) PRIMARY KEY,
    slot_id VARCHAR(36) NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CONFIRMED',
    CONSTRAINT check_booking_status CHECK (status IN ('CONFIRMED', 'CANCELLED'))
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_slots_owner ON slots(owner_id);
CREATE INDEX idx_waitlist_slot_joined ON waitlist_entries(slot_id, joined_at ASC);
CREATE INDEX idx_holds_slot ON holds(slot_id);
CREATE INDEX idx_bookings_slot ON bookings(slot_id);
