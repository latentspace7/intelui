CREATE SCHEMA airline;

CREATE SCHEMA app;


CREATE TABLE airline.aircraft (
	id SERIAL NOT NULL, 
	registration VARCHAR(15) NOT NULL, 
	model VARCHAR(50) NOT NULL, 
	seats INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (seats > 0), 
	UNIQUE (registration)
)

;


CREATE TABLE airline.customers (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	loyalty_member BOOLEAN NOT NULL, 
	loyalty_tier VARCHAR(20) NOT NULL, 
	registered_at DATE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (loyalty_tier IN ('None', 'Silver', 'Gold', 'Platinum')), 
	UNIQUE (email)
)

;


CREATE TABLE app.analyses (
	id VARCHAR(36) NOT NULL, 
	parent_id VARCHAR(36), 
	question TEXT NOT NULL, 
	snapshot JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES app.analyses (id)
)

;

CREATE INDEX ix_app_analyses_created_at ON app.analyses (created_at);


CREATE TABLE airline.flights (
	id SERIAL NOT NULL, 
	flight_number VARCHAR(10) NOT NULL, 
	origin VARCHAR(3) NOT NULL, 
	destination VARCHAR(3) NOT NULL, 
	aircraft_id INTEGER NOT NULL, 
	scheduled_departure TIMESTAMP WITH TIME ZONE NOT NULL, 
	scheduled_arrival TIMESTAMP WITH TIME ZONE NOT NULL, 
	actual_departure TIMESTAMP WITH TIME ZONE, 
	actual_arrival TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(20) NOT NULL, 
	delay_minutes INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (origin <> destination), 
	CHECK (scheduled_arrival > scheduled_departure), 
	CHECK (delay_minutes >= 0), 
	CHECK (status IN ('Arrived', 'Delayed', 'Cancelled')), 
	CHECK ((status = 'Cancelled' AND actual_departure IS NULL AND actual_arrival IS NULL) OR (status <> 'Cancelled' AND actual_departure IS NOT NULL AND actual_arrival > actual_departure)), 
	FOREIGN KEY(aircraft_id) REFERENCES airline.aircraft (id)
)

;

CREATE INDEX ix_airline_flights_scheduled_departure ON airline.flights (scheduled_departure);

CREATE INDEX ix_airline_flights_status ON airline.flights (status);


CREATE TABLE app.reports (
	id VARCHAR(36) NOT NULL, 
	analysis_id VARCHAR(36) NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	question TEXT NOT NULL, 
	snapshot JSON NOT NULL, 
	position INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_refreshed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_attempt_at TIMESTAMP WITH TIME ZONE, 
	refresh_interval_hours INTEGER NOT NULL, 
	next_refresh_at TIMESTAMP WITH TIME ZONE, 
	refresh_status VARCHAR(20) NOT NULL, 
	refresh_error VARCHAR(500), 
	PRIMARY KEY (id), 
	CHECK (refresh_interval_hours IN (0, 1, 4, 12, 24)), 
	FOREIGN KEY(analysis_id) REFERENCES app.analyses (id)
)

;

CREATE INDEX ix_reports_next_refresh_at ON app.reports (next_refresh_at);


CREATE TABLE airline.bookings (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	flight_id INTEGER NOT NULL, 
	booking_reference VARCHAR(12) NOT NULL, 
	booked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	travel_class VARCHAR(20) NOT NULL, 
	ticket_status VARCHAR(20) NOT NULL, 
	total_amount NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (total_amount >= 0), 
	CHECK (travel_class IN ('Economy', 'Premium Economy', 'Business', 'First Class')), 
	CHECK (ticket_status IN ('Flown', 'Cancelled', 'Refunded')), 
	FOREIGN KEY(customer_id) REFERENCES airline.customers (id), 
	FOREIGN KEY(flight_id) REFERENCES airline.flights (id), 
	UNIQUE (booking_reference)
)

;

CREATE INDEX ix_airline_bookings_booked_at ON airline.bookings (booked_at);

CREATE INDEX ix_airline_bookings_customer_id ON airline.bookings (customer_id);

CREATE INDEX ix_airline_bookings_flight_id ON airline.bookings (flight_id);


CREATE TABLE airline.complaints (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	booking_id INTEGER NOT NULL, 
	flight_id INTEGER NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	severity VARCHAR(10) NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	resolution_details TEXT, 
	PRIMARY KEY (id), 
	CHECK (status IN ('Open', 'In Progress', 'Resolved')), 
	CHECK (resolved_at IS NULL OR resolved_at >= submitted_at), 
	FOREIGN KEY(customer_id) REFERENCES airline.customers (id), 
	FOREIGN KEY(booking_id) REFERENCES airline.bookings (id), 
	FOREIGN KEY(flight_id) REFERENCES airline.flights (id)
)

;

CREATE INDEX ix_airline_complaints_booking_id ON airline.complaints (booking_id);

CREATE INDEX ix_airline_complaints_customer_id ON airline.complaints (customer_id);

CREATE INDEX ix_airline_complaints_flight_id ON airline.complaints (flight_id);

CREATE INDEX ix_airline_complaints_status ON airline.complaints (status);


CREATE TABLE airline.payments (
	id SERIAL NOT NULL, 
	booking_id INTEGER NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	paid_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	method VARCHAR(25) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (amount > 0), 
	CHECK (status IN ('Completed', 'Refunded', 'Refund Pending')), 
	UNIQUE (booking_id), 
	FOREIGN KEY(booking_id) REFERENCES airline.bookings (id)
)

;


CREATE TABLE airline.service_requests (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	booking_id INTEGER NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	description TEXT NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CHECK (status IN ('Open', 'In Progress', 'Resolved')), 
	CHECK (resolved_at IS NULL OR resolved_at >= created_at), 
	FOREIGN KEY(customer_id) REFERENCES airline.customers (id), 
	FOREIGN KEY(booking_id) REFERENCES airline.bookings (id)
)

;

CREATE INDEX ix_airline_service_requests_booking_id ON airline.service_requests (booking_id);

CREATE INDEX ix_airline_service_requests_customer_id ON airline.service_requests (customer_id);

CREATE INDEX ix_airline_service_requests_status ON airline.service_requests (status);


CREATE TABLE airline.conversations (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	service_request_id INTEGER, 
	complaint_id INTEGER, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	channel VARCHAR(10) NOT NULL, 
	participants VARCHAR(200) NOT NULL, 
	summary TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (service_request_id IS NOT NULL OR complaint_id IS NOT NULL), 
	FOREIGN KEY(customer_id) REFERENCES airline.customers (id), 
	FOREIGN KEY(service_request_id) REFERENCES airline.service_requests (id), 
	FOREIGN KEY(complaint_id) REFERENCES airline.complaints (id)
)

;

CREATE INDEX ix_airline_conversations_customer_id ON airline.conversations (customer_id);

GRANT USAGE ON SCHEMA airline TO airline_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA airline TO airline_reader;

ALTER ROLE airline_reader SET temp_file_limit = '16MB';
