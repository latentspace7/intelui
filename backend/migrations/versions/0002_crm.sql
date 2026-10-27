CREATE SCHEMA crm;

CREATE TABLE crm.audit_events (
	id SERIAL NOT NULL, 
	entity VARCHAR(30) NOT NULL, 
	record_id INTEGER NOT NULL, 
	previous_status VARCHAR(30) NOT NULL, 
	new_status VARCHAR(30) NOT NULL, 
	actor VARCHAR(60) NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE crm.products (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	monthly_unit_price NUMERIC(12, 2) NOT NULL, 
	setup_fee NUMERIC(12, 2) NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (monthly_unit_price >= 0 AND setup_fee >= 0)
);

CREATE TABLE crm.staff (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	team VARCHAR(60) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE crm.companies (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	industry VARCHAR(60) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	region VARCHAR(60) NOT NULL, 
	owner_id INTEGER NOT NULL, 
	annual_revenue NUMERIC(14, 2) NOT NULL, 
	monthly_income NUMERIC(12, 2) NOT NULL, 
	monthly_expenses NUMERIC(12, 2) NOT NULL, 
	monthly_budget NUMERIC(12, 2) NOT NULL, 
	description TEXT NOT NULL, 
	created_at DATE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (annual_revenue >= 0 AND monthly_income >= 0 AND monthly_expenses >= 0 AND monthly_budget >= 0), 
	UNIQUE (name), 
	FOREIGN KEY(owner_id) REFERENCES crm.staff (id)
);

CREATE INDEX ix_crm_companies_owner_id ON crm.companies (owner_id);

CREATE TABLE crm.cash_entries (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	occurred_at DATE NOT NULL, 
	description VARCHAR(150) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	direction VARCHAR(20) NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (direction IN ('Inflow', 'Outflow') AND amount > 0), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id)
);

CREATE INDEX ix_crm_cash_entries_company_id ON crm.cash_entries (company_id);

CREATE TABLE crm.contacts (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	role VARCHAR(60) NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	UNIQUE (email)
);

CREATE INDEX ix_crm_contacts_company_id ON crm.contacts (company_id);

CREATE TABLE crm.documents (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	document_type VARCHAR(60) NOT NULL, 
	body TEXT NOT NULL, 
	received_at DATE NOT NULL, 
	expires_at DATE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id)
);

CREATE INDEX ix_crm_documents_company_id ON crm.documents (company_id);

CREATE TABLE crm.milestones (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	due_date DATE NOT NULL, 
	sequence INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (status IN ('Complete', 'In progress', 'Blocked', 'Upcoming')), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(owner_id) REFERENCES crm.staff (id)
);

CREATE INDEX ix_crm_milestones_company_id ON crm.milestones (company_id);

CREATE INDEX ix_crm_milestones_owner_id ON crm.milestones (owner_id);

CREATE TABLE crm.quotes (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	months INTEGER NOT NULL, 
	discount_percent NUMERIC(5, 2) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (quantity BETWEEN 1 AND 10000 AND months BETWEEN 1 AND 120 AND discount_percent BETWEEN 0 AND 100), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(product_id) REFERENCES crm.products (id)
);

CREATE INDEX ix_crm_quotes_company_id ON crm.quotes (company_id);

CREATE INDEX ix_crm_quotes_product_id ON crm.quotes (product_id);

CREATE TABLE crm.relationships (
	id SERIAL NOT NULL, 
	source_company_id INTEGER NOT NULL, 
	target_company_id INTEGER NOT NULL, 
	relationship VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (source_company_id <> target_company_id), 
	FOREIGN KEY(source_company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(target_company_id) REFERENCES crm.companies (id)
);

CREATE INDEX ix_crm_relationships_source_company_id ON crm.relationships (source_company_id);

CREATE INDEX ix_crm_relationships_target_company_id ON crm.relationships (target_company_id);

CREATE TABLE crm.rule_checks (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	observed_value NUMERIC(14, 2), 
	threshold NUMERIC(14, 2) NOT NULL, 
	operator VARCHAR(5) NOT NULL, 
	description TEXT NOT NULL, 
	rule_version VARCHAR(30) NOT NULL, 
	evaluated_at DATE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (operator IN ('gte', 'lte', 'eq')), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id)
);

CREATE INDEX ix_crm_rule_checks_company_id ON crm.rule_checks (company_id);

CREATE TABLE crm.activities (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	contact_id INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	description TEXT NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(contact_id) REFERENCES crm.contacts (id), 
	FOREIGN KEY(owner_id) REFERENCES crm.staff (id)
);

CREATE INDEX ix_crm_activities_company_id ON crm.activities (company_id);

CREATE INDEX ix_crm_activities_contact_id ON crm.activities (contact_id);

CREATE INDEX ix_crm_activities_owner_id ON crm.activities (owner_id);

CREATE TABLE crm.deals (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	contact_id INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	stage VARCHAR(30) NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	probability INTEGER NOT NULL, 
	created_at DATE NOT NULL, 
	expected_close DATE NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (amount >= 0 AND probability BETWEEN 0 AND 100), 
	CHECK (stage IN ('Lead', 'Qualified', 'Proposal', 'Negotiation', 'Won', 'Lost')), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(contact_id) REFERENCES crm.contacts (id), 
	FOREIGN KEY(owner_id) REFERENCES crm.staff (id)
);

CREATE INDEX ix_crm_deals_company_id ON crm.deals (company_id);

CREATE INDEX ix_crm_deals_contact_id ON crm.deals (contact_id);

CREATE INDEX ix_crm_deals_owner_id ON crm.deals (owner_id);

CREATE TABLE crm.document_fields (
	id SERIAL NOT NULL, 
	document_id INTEGER NOT NULL, 
	field_name VARCHAR(80) NOT NULL, 
	declared_value VARCHAR(200) NOT NULL, 
	extracted_value VARCHAR(200) NOT NULL, 
	review_status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (review_status IN ('Pending', 'Accepted', 'Needs correction')), 
	FOREIGN KEY(document_id) REFERENCES crm.documents (id)
);

CREATE INDEX ix_crm_document_fields_document_id ON crm.document_fields (document_id);

CREATE TABLE crm.tasks (
	id SERIAL NOT NULL, 
	company_id INTEGER NOT NULL, 
	deal_id INTEGER NOT NULL, 
	owner_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	due_date DATE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (status IN ('Outstanding', 'In progress', 'Complete')), 
	FOREIGN KEY(company_id) REFERENCES crm.companies (id), 
	FOREIGN KEY(deal_id) REFERENCES crm.deals (id), 
	FOREIGN KEY(owner_id) REFERENCES crm.staff (id)
);

CREATE INDEX ix_crm_tasks_company_id ON crm.tasks (company_id);

CREATE INDEX ix_crm_tasks_deal_id ON crm.tasks (deal_id);

CREATE INDEX ix_crm_tasks_owner_id ON crm.tasks (owner_id);

GRANT USAGE ON SCHEMA crm TO airline_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA crm TO airline_reader;
