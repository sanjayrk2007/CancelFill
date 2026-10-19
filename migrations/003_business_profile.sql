CREATE TABLE IF NOT EXISTS businesses (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	business_name VARCHAR(255) NOT NULL,
	category VARCHAR(50) NOT NULL,
	contact_phone VARCHAR(32) NOT NULL,
	contact_address TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	CONSTRAINT ck_business_category CHECK (category IN ('SALON', 'TUTOR', 'SPORTS', 'CLINIC', 'SERVICE_CENTER', 'OTHER')),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_businesses_user_id ON businesses (user_id);
