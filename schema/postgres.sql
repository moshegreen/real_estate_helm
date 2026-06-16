-- PostgreSQL/PostGIS target schema for the server-backed product.
-- This is the normalized destination for the current local JSON deal state.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE deals (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  status text NOT NULL,
  asset_type text,
  source text,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE deal_status_history (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  from_status text NOT NULL,
  to_status text NOT NULL,
  actor text NOT NULL,
  reason text NOT NULL,
  occurred_at timestamptz NOT NULL
);

CREATE TABLE addresses (
  id uuid PRIMARY KEY,
  line1 text NOT NULL,
  city text,
  state text,
  country text,
  postal_code text,
  location geography(Point, 4326)
);

CREATE TABLE parcels (
  id uuid PRIMARY KEY,
  parcel_number text NOT NULL,
  jurisdiction text,
  zoning text,
  flood_zone text,
  boundary geography(Polygon, 4326)
);

CREATE TABLE assets (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  address_id uuid REFERENCES addresses(id),
  parcel_ref_id uuid REFERENCES parcels(id),
  name text NOT NULL,
  address text,
  city text,
  state text,
  country text,
  parcel_id text,
  asset_type text,
  unit_count integer,
  building_size numeric,
  land_size numeric,
  year_built integer,
  location geography(Point, 4326)
);

CREATE TABLE documents (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  document_type text NOT NULL,
  storage_uri text NOT NULL,
  sha256 text,
  uploaded_by text NOT NULL,
  uploaded_at timestamptz NOT NULL
);

CREATE TABLE document_pages (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents(id),
  page_number integer NOT NULL,
  text_content text,
  image_uri text,
  extracted_tables jsonb NOT NULL DEFAULT '[]'
);

CREATE TABLE extracted_facts (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  field_name text NOT NULL,
  value jsonb NOT NULL,
  confidence numeric NOT NULL,
  status text NOT NULL,
  source jsonb NOT NULL,
  extracted_at timestamptz NOT NULL,
  reviewed_at timestamptz,
  reviewer text,
  review_note text
);

CREATE TABLE fact_sources (
  id uuid PRIMARY KEY,
  fact_id uuid NOT NULL REFERENCES extracted_facts(id),
  document_id uuid REFERENCES documents(id),
  document_page_id uuid REFERENCES document_pages(id),
  spreadsheet_cell_id uuid,
  source_kind text NOT NULL,
  context text
);

CREATE TABLE spreadsheets (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  document_id uuid NOT NULL REFERENCES documents(id),
  name text NOT NULL,
  imported_at timestamptz NOT NULL
);

CREATE TABLE spreadsheet_cells (
  id uuid PRIMARY KEY,
  spreadsheet_id uuid NOT NULL REFERENCES spreadsheets(id),
  sheet text NOT NULL,
  cell text NOT NULL,
  value jsonb,
  formula text,
  mapped_field text,
  warning text
);

ALTER TABLE fact_sources
  ADD CONSTRAINT fact_sources_spreadsheet_cell_fk
  FOREIGN KEY (spreadsheet_cell_id) REFERENCES spreadsheet_cells(id);

CREATE TABLE assumptions (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  scenario_id uuid,
  name text NOT NULL,
  value jsonb NOT NULL,
  rationale text NOT NULL,
  source_fact_id uuid,
  created_at timestamptz NOT NULL
);

CREATE TABLE scenarios (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  scenario_type text NOT NULL,
  outputs jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL
);

CREATE TABLE scenario_outputs (
  id uuid PRIMARY KEY,
  scenario_id uuid NOT NULL REFERENCES scenarios(id),
  metric_name text NOT NULL,
  value jsonb NOT NULL,
  unit text,
  calculated_at timestamptz NOT NULL
);

CREATE TABLE cash_flows (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  period text NOT NULL,
  category text NOT NULL,
  cash_flow_type text NOT NULL,
  amount numeric NOT NULL,
  source jsonb
);

CREATE TABLE cash_flows_projected (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  scenario_id uuid REFERENCES scenarios(id),
  period text NOT NULL,
  category text NOT NULL,
  amount numeric NOT NULL,
  source jsonb
);

CREATE TABLE cash_flows_actual (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  period text NOT NULL,
  category text NOT NULL,
  amount numeric NOT NULL,
  source jsonb
);

CREATE TABLE debt_terms (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  lender text,
  debt_amount numeric,
  interest_rate numeric,
  maturity_date date,
  amortization_years integer,
  covenant_dscr numeric
);

CREATE TABLE rent_rolls (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  as_of_date date NOT NULL,
  unit text,
  tenant_name text,
  monthly_rent numeric,
  market_rent numeric,
  occupied boolean NOT NULL DEFAULT true,
  concessions numeric,
  bad_debt numeric,
  lease_start date,
  lease_end date,
  source jsonb
);

CREATE TABLE tenants (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  credit_notes text
);

CREATE TABLE leases (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  unit text,
  start_date date,
  end_date date,
  annual_rent numeric,
  renewal_probability numeric
);

CREATE TABLE capex_items (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  category text,
  budgeted_amount numeric NOT NULL,
  actual_amount numeric
);

CREATE TABLE development_budgets (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  land_cost numeric NOT NULL DEFAULT 0,
  hard_costs numeric NOT NULL DEFAULT 0,
  soft_costs numeric NOT NULL DEFAULT 0,
  contingency numeric NOT NULL DEFAULT 0
);

CREATE TABLE development_milestones (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  target_date date NOT NULL,
  actual_date date,
  status text NOT NULL
);

CREATE TABLE web_sources (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  title text NOT NULL,
  url text NOT NULL,
  source_type text NOT NULL,
  retrieved_at timestamptz NOT NULL
);

CREATE TABLE market_comps (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  name text NOT NULL,
  comp_type text NOT NULL,
  value numeric NOT NULL,
  address text,
  distance_miles numeric,
  source text
);

CREATE TABLE property_records (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  source text NOT NULL,
  parcel_id text,
  assessed_value numeric,
  owner_name text,
  zoning text,
  flood_zone text,
  year_built integer,
  building_size numeric,
  land_size numeric
);

CREATE TABLE location_context (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  item_type text NOT NULL,
  name text NOT NULL,
  distance_miles numeric,
  source text,
  notes text,
  location geography(Point, 4326)
);

CREATE TABLE permit_events (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  permit_number text NOT NULL,
  permit_type text NOT NULL,
  status text NOT NULL,
  filed_date date,
  issued_date date,
  description text,
  source_url text
);

CREATE TABLE news_events (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  title text NOT NULL,
  url text NOT NULL,
  classification text NOT NULL,
  published_at date,
  summary text
);

CREATE TABLE imagery_snapshots (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  captured_at date NOT NULL,
  storage_uri text NOT NULL,
  source text NOT NULL,
  notes text
);

CREATE TABLE alerts (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  severity text NOT NULL,
  category text NOT NULL,
  title text NOT NULL,
  description text NOT NULL,
  source text NOT NULL,
  financial_impact numeric,
  recommended_action text,
  owner text,
  due_date date,
  status text NOT NULL,
  created_at timestamptz NOT NULL,
  resolved_at timestamptz
);

CREATE TABLE investment_decisions (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  recommendation text NOT NULL,
  actor text NOT NULL,
  rationale text NOT NULL,
  decided_at timestamptz NOT NULL
);

CREATE TABLE tasks (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  title text NOT NULL,
  owner text,
  due_date date,
  status text NOT NULL
);

CREATE TABLE obligations (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  title text NOT NULL,
  due_date date NOT NULL,
  obligation_type text NOT NULL,
  amount numeric,
  source text,
  owner text
);

CREATE TABLE comments (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  author text NOT NULL,
  body text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  created_at timestamptz NOT NULL,
  resolved_at timestamptz
);

CREATE TABLE approval_requests (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  title text NOT NULL,
  requested_by text NOT NULL,
  approver text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  status text NOT NULL,
  requested_at timestamptz NOT NULL,
  decided_at timestamptz,
  decision_note text
);

CREATE TABLE notifications (
  id uuid PRIMARY KEY,
  deal_id uuid NOT NULL REFERENCES deals(id),
  channel text NOT NULL,
  recipient text NOT NULL,
  title text NOT NULL,
  body text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  created_at timestamptz NOT NULL
);

CREATE TABLE audit_log (
  id bigserial PRIMARY KEY,
  actor text NOT NULL,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id uuid NOT NULL,
  reason text,
  occurred_at timestamptz NOT NULL
);

CREATE INDEX assets_location_idx ON assets USING gist(location);
CREATE INDEX addresses_location_idx ON addresses USING gist(location);
CREATE INDEX parcels_boundary_idx ON parcels USING gist(boundary);
CREATE INDEX alerts_open_idx ON alerts(deal_id, status, severity);
CREATE INDEX extracted_facts_status_idx ON extracted_facts(deal_id, status);
CREATE INDEX approval_requests_status_idx ON approval_requests(deal_id, status);
CREATE INDEX notifications_recipient_idx ON notifications(recipient, channel);
CREATE INDEX property_records_parcel_idx ON property_records(parcel_id);
CREATE INDEX location_context_location_idx ON location_context USING gist(location);
CREATE INDEX permit_events_status_idx ON permit_events(deal_id, status);
CREATE INDEX obligations_due_date_idx ON obligations(deal_id, due_date, obligation_type);
