-- 002: slot capacity attribute, password reset (FR-05), notifications (FR-37..39), payments (FR-40..42)

-- Slot capacity (FR-06): descriptive only. A slot is still one bookable unit with at most one
-- confirmed booking and one active hold (NFR-03); the existing unique indexes are unchanged.
ALTER TABLE slots ADD COLUMN IF NOT EXISTS capacity INTEGER NOT NULL DEFAULT 1;
ALTER TABLE slots DROP CONSTRAINT IF EXISTS ck_slot_capacity;
ALTER TABLE slots ADD CONSTRAINT ck_slot_capacity CHECK (capacity >= 1);

-- Holds can now be waitlist offers or seat reservations during checkout.
ALTER TABLE holds ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'OFFER';
ALTER TABLE holds DROP CONSTRAINT IF EXISTS ck_hold_kind;
ALTER TABLE holds ADD CONSTRAINT ck_hold_kind CHECK (kind IN ('OFFER', 'CHECKOUT'));

-- Contact details and notification preferences.
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(32);
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_email BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_sms BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_push BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
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
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);

CREATE TABLE IF NOT EXISTS push_subscriptions (
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
CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user_id ON push_subscriptions (user_id);

CREATE TABLE IF NOT EXISTS notifications (
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
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);

CREATE TABLE IF NOT EXISTS notification_deliveries (
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
CREATE INDEX IF NOT EXISTS ix_delivery_pending ON notification_deliveries (status, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_notification_deliveries_notification_id ON notification_deliveries (notification_id);

CREATE TABLE IF NOT EXISTS payments (
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
CREATE INDEX IF NOT EXISTS ix_payments_booking_id ON payments (booking_id);
CREATE INDEX IF NOT EXISTS ix_payments_hold_id ON payments (hold_id);
CREATE INDEX IF NOT EXISTS ix_payments_slot_id ON payments (slot_id);
CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments (user_id);
