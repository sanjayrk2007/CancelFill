-- CancelFill - PostgreSQL reference schema (generated from app/models.py).
-- The app creates missing tables on startup; for an existing database apply migrations/*.sql instead.

DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS notification_deliveries CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS push_subscriptions CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS holds CASCADE;
DROP TABLE IF EXISTS waitlist_entries CASCADE;
DROP TABLE IF EXISTS slots CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	phone VARCHAR(32), 
	notify_email BOOLEAN NOT NULL, 
	notify_sms BOOLEAN NOT NULL, 
	notify_push BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE slots (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	resource_id VARCHAR(255) NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	capacity INTEGER DEFAULT '1' NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_slot_status CHECK (status IN ('AVAILABLE', 'BOOKED', 'HELD', 'CANCELLED')), 
	CONSTRAINT ck_slot_capacity CHECK (capacity >= 1), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_slots_owner_id ON slots (owner_id);
CREATE INDEX ix_slots_resource_id ON slots (resource_id);

CREATE TABLE waitlist_entries (
	id VARCHAR(36) NOT NULL, 
	slot_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	joined_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_waitlist_status CHECK (status IN ('WAITING', 'OFFERED', 'CANCELLED', 'EXPIRED', 'CONFIRMED', 'DECLINED')), 
	FOREIGN KEY(slot_id) REFERENCES slots (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_waitlist_entries_slot_id ON waitlist_entries (slot_id);
CREATE INDEX ix_waitlist_entries_user_id ON waitlist_entries (user_id);
CREATE UNIQUE INDEX uq_active_waitlist_per_slot_user ON waitlist_entries (slot_id, user_id) WHERE status IN ('WAITING', 'OFFERED');

CREATE TABLE holds (
	id VARCHAR(36) NOT NULL, 
	slot_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	kind VARCHAR(20) DEFAULT 'OFFER' NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_hold_status CHECK (status IN ('ACTIVE', 'EXPIRED', 'RELEASED', 'CONFIRMED', 'DECLINED')), 
	CONSTRAINT ck_hold_kind CHECK (kind IN ('OFFER', 'CHECKOUT')), 
	FOREIGN KEY(slot_id) REFERENCES slots (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_holds_slot_id ON holds (slot_id);
CREATE INDEX ix_holds_user_id ON holds (user_id);
CREATE UNIQUE INDEX uq_active_hold_per_slot ON holds (slot_id) WHERE status = 'ACTIVE';

CREATE TABLE bookings (
	id VARCHAR(36) NOT NULL, 
	slot_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	booked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	recovered_from_booking_id VARCHAR(36), 
	cancellation_reason TEXT, 
	cancelled_by_role VARCHAR(50), 
	PRIMARY KEY (id), 
	CONSTRAINT ck_booking_status CHECK (status IN ('CONFIRMED', 'CANCELLED')), 
	CONSTRAINT ck_booking_source CHECK (source IN ('DIRECT', 'RECOVERED')), 
	FOREIGN KEY(slot_id) REFERENCES slots (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(recovered_from_booking_id) REFERENCES bookings (id) ON DELETE SET NULL
);
CREATE INDEX ix_bookings_slot_id ON bookings (slot_id);
CREATE INDEX ix_bookings_user_id ON bookings (user_id);
CREATE UNIQUE INDEX uq_confirmed_booking_per_slot ON bookings (slot_id) WHERE status = 'CONFIRMED';

CREATE TABLE password_reset_tokens (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
);
CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);

CREATE TABLE push_subscriptions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	endpoint TEXT NOT NULL, 
	p256dh VARCHAR(255) NOT NULL, 
	auth VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (endpoint)
);
CREATE INDEX ix_push_subscriptions_user_id ON push_subscriptions (user_id);

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	body TEXT NOT NULL, 
	link VARCHAR(255), 
	show_in_app BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	read_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE notification_deliveries (
	id VARCHAR(36) NOT NULL, 
	notification_id VARCHAR(36) NOT NULL, 
	channel VARCHAR(10) NOT NULL, 
	destination TEXT NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_error TEXT, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_delivery_channel CHECK (channel IN ('EMAIL', 'SMS', 'PUSH')), 
	CONSTRAINT ck_delivery_status CHECK (status IN ('PENDING', 'SENT', 'FAILED')), 
	FOREIGN KEY(notification_id) REFERENCES notifications (id) ON DELETE CASCADE
);
CREATE INDEX ix_delivery_pending ON notification_deliveries (status, next_attempt_at);
CREATE INDEX ix_notification_deliveries_notification_id ON notification_deliveries (notification_id);

CREATE TABLE payments (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	slot_id VARCHAR(36) NOT NULL, 
	hold_id VARCHAR(36), 
	booking_id VARCHAR(36), 
	amount NUMERIC(10, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	provider_order_id VARCHAR(100) NOT NULL, 
	provider_payment_id VARCHAR(100), 
	status VARCHAR(20) NOT NULL, 
	refund_id VARCHAR(100), 
	refund_reason TEXT, 
	refund_attempts INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	paid_at TIMESTAMP WITH TIME ZONE, 
	refunded_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_payment_status CHECK (status IN ('CREATED', 'PAID', 'FAILED', 'EXPIRED', 'REFUND_PENDING', 'REFUNDED', 'REFUND_FAILED')), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(slot_id) REFERENCES slots (id) ON DELETE CASCADE, 
	FOREIGN KEY(hold_id) REFERENCES holds (id) ON DELETE SET NULL, 
	FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE SET NULL, 
	UNIQUE (provider_order_id), 
	UNIQUE (provider_payment_id)
);
CREATE INDEX ix_payments_booking_id ON payments (booking_id);
CREATE INDEX ix_payments_hold_id ON payments (hold_id);
CREATE INDEX ix_payments_slot_id ON payments (slot_id);
CREATE INDEX ix_payments_user_id ON payments (user_id);
