CREATE ROLE airline_reader LOGIN PASSWORD 'reader_demo' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
ALTER ROLE airline_reader SET default_transaction_read_only = on;
ALTER ROLE airline_reader SET statement_timeout = '5s';
ALTER ROLE airline_reader SET idle_in_transaction_session_timeout = '15s';
ALTER ROLE airline_reader SET search_path = airline, pg_catalog;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE TEMPORARY ON DATABASE aerovista FROM PUBLIC;
