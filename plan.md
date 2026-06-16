# Real Estate Investment Dashboard and Analysis Tool
## 1. Product Vision
Build a **real-estate deal intelligence system** for a family office portfolio manager.
The system should not be just a dashboard with AI features added on. It should function as a **deal operating system** where every prospectus, spreadsheet, assumption, extracted fact, web source, alert, cash-flow update, and investment decision becomes structured, versioned, and monitorable.
The core object is a **Deal**.
Each deal should contain:
- uploaded documents
- Excel underwriting sheets
- extracted facts
- financial assumptions
- scenarios
- web-enriched intelligence
- local news
- maps and satellite imagery
- comparable deals
- decision history
- cash-flow updates
- development progress
- alerts
- actual performance over time
The system should support both:
1. **Deals entered into**
2. **Deals not entered into**
This second category is important because it allows the family office to build a long-term institutional memory of rejected deals, missed opportunities, underwriting discipline, and what-if analysis.
---
## 2. Primary Platforms
### Primary App
**Windows desktop app**
This is where the portfolio manager should do the full workflow:
- upload documents
- review extracted facts
- inspect Excel models
- run underwriting
- compare scenarios
- review maps and comps
- generate investment committee material
- monitor portfolio performance
### Secondary App
**Android companion app**
The Android app should focus on:
- alerts
- quick deal summaries
- mobile review
- push notifications
- maps
- comments
- approvals
- escalation of urgent issues
The Android app should not be expected to carry the full underwriting workflow. It should be used for monitoring, reviewing, and reacting.
---
## 3. Main Inputs
The system receives:
- deal prospectuses
- offering memoranda
- PDFs
- Excel underwriting sheets
- rent rolls
- debt term sheets
- construction budgets
- appraisals
- inspection reports
- broker memos
- permits
- market reports
- property management reports
- monthly cash-flow statements
- sponsor updates
Later versions could also ingest:
- emails
- data rooms
- photos
- drone imagery
- bank statements
- accounting exports
- CRM exports
- legal documents
---
## 4. Core Deal Model
Every opportunity should have a durable record, even if it is rejected.
```text
Deal
 ├── Identity
 │    ├── name
 │    ├── address
 │    ├── parcel
 │    ├── coordinates
 │    ├── asset type
 │    ├── sponsor
 │    ├── broker
 │    ├── seller
 │    └── source
 │
 ├── Status
 │    ├── new
 │    ├── screening
 │    ├── underwriting
 │    ├── investment committee
 │    ├── LOI
 │    ├── diligence
 │    ├── acquired
 │    ├── rejected
 │    └── watchlist
 │
 ├── Documents
 ├── Extracted facts
 ├── Assumptions
 ├── Scenarios
 ├── Investment committee notes
 ├── Monitoring feeds
 ├── Alerts
 └── Actual performance

The system should preserve the history of each deal:

* when it was received
* who sourced it
* what assumptions were used
* why it was accepted or rejected
* what happened afterward
* whether actual results matched underwriting

⸻

5. Deal Intake Workflow

Step 1: Create Deal

The user creates a new deal manually or imports one from a document, email, folder, or data room.

Basic fields:

* deal name
* property address
* asset type
* broker / sponsor / seller
* acquisition price
* target close date
* status
* owner / analyst

Step 2: Upload Documents

Supported files:

* PDF
* Excel
* CSV
* Word
* images
* zipped data rooms

Step 3: Extract Data

The system extracts:

* property address
* purchase price
* NOI
* cap rate
* rent roll
* occupancy
* asset size
* land area
* unit count
* debt terms
* projected returns
* sources and uses
* construction budget
* timeline
* sponsor claims
* market claims
* comparable sales
* lease information

Step 4: Human Review

Extracted data should not automatically become trusted.

The system should show:

* extracted value
* confidence score
* source document
* page number
* table
* Excel sheet
* Excel cell
* surrounding context

The user can:

* accept
* reject
* edit
* mark as assumption
* mark as sponsor claim
* request re-extraction

Step 5: Canonical Underwriting

The accepted data is mapped into the canonical financial model.

⸻

6. Core Principle: Fact vs Assumption vs Output

The system must separate:

Fact ≠ Assumption ≠ Output

Example:

Fact:
  Broker OM says current NOI is $1.2M.
Assumption:
  Year-3 stabilized NOI is $1.45M.
Output:
  Base-case IRR is 14.8%.

This distinction is critical.

The system should never confuse a sponsor claim with a verified fact, and it should never confuse an underwriting assumption with an actual result.

⸻

7. Financial Analysis Engine

The financial engine should support both deal-level and portfolio-level analysis.

Deal-Level Metrics

Minimum metrics:

* purchase price
* equity required
* debt amount
* loan-to-value
* loan-to-cost
* going-in cap rate
* stabilized cap rate
* net operating income
* EBITDA, where applicable
* debt service coverage ratio
* debt yield
* cash-on-cash return
* internal rate of return
* equity multiple
* payback period
* break-even occupancy
* exit value
* refinance proceeds
* hold period return
* total profit
* downside loss exposure

Sensitivities

The system should support sensitivity analysis for:

* rent growth
* occupancy
* exit cap rate
* interest rate
* construction cost
* operating expenses
* lease-up speed
* refinancing terms
* sale date
* terminal value
* tax assumptions
* inflation
* insurance cost
* maintenance reserves

Development Deal Metrics

For development deals:

* land cost
* hard costs
* soft costs
* contingency
* interest reserve
* total project cost
* construction timeline
* lease-up timeline
* projected completion value
* yield on cost
* margin on cost
* development spread
* draw schedule
* budget variance
* delay impact
* cost overrun impact
* permit risk
* entitlement risk

Income-Producing Asset Metrics

For stabilized or semi-stabilized assets:

* rent roll
* lease expiry schedule
* occupancy
* vacancy
* bad debt
* concessions
* renewal probability
* market rent gap
* tenant concentration
* weighted average lease term
* trailing NOI
* underwritten NOI
* actual NOI
* variance to budget

⸻

8. Scenario Engine

Scenarios should be first-class objects.

Each scenario should preserve its own assumptions.

Scenario
 ├── sponsor case
 ├── analyst base case
 ├── downside case
 ├── upside case
 ├── investment committee case
 ├── acquisition case
 ├── current reforecast
 └── actuals

The user should be able to compare:

* sponsor case vs internal base case
* original underwriting vs actuals
* rejected deal case vs later market outcome
* downside case vs current reforecast
* one financing structure vs another
* buy vs pass
* hold vs sell
* refinance vs sell

⸻

9. Deals Not Entered

The system should preserve rejected deals.

This creates a shadow portfolio.

For rejected deals, store:

* reason for rejection
* assumptions at time of review
* key risks
* proposed price
* target return
* broker / sponsor
* market
* competing buyer if known
* later sale price if known
* later performance if known
* whether rejection was correct in hindsight

Useful questions:

* Did we pass on deals that later outperformed?
* Which brokers consistently send inflated numbers?
* Which geographies have produced the best missed opportunities?
* Which asset classes were wrongly avoided?
* Which underwriting assumptions were too conservative?
* Which deals would have improved the portfolio?
* Which rejected deals should be re-opened?

⸻

10. Web-Enriched Intelligence

The dashboard should pull pertinent information from the web and external datasets.

Map and Location Context

For each property:

* map
* satellite view
* street view, where available
* parcel boundaries
* nearby roads
* public transit
* schools
* hospitals
* retail nodes
* employment centers
* infrastructure
* zoning overlays
* flood zones
* environmental risks
* nearby construction
* competing properties

Satellite Imagery

Satellite imagery can be used for:

* construction progress monitoring
* nearby development detection
* land clearing detection
* parking-lot utilization
* roof condition signals
* site activity verification
* comparison of imagery over time
* before/after acquisition monitoring

Potential sources:

* Google Maps Platform
* Sentinel Hub
* Copernicus data
* Planet
* local GIS portals
* municipal imagery
* drone imagery where available

Local News

The system should monitor local news around each asset.

Topics to watch:

* zoning changes
* planning board decisions
* building permits
* local crime
* infrastructure projects
* transit changes
* fires
* floods
* storms
* lawsuits
* environmental issues
* tenant bankruptcies
* major employer openings
* major employer closures
* protests
* school district changes
* municipal tax changes
* political opposition to development
* competing developments

Classify news as:

Material positive
Material negative
Watch
Noise
Duplicate

Comparable Deals

Track:

* local sales
* local listings
* local rents
* local cap rates
* nearby development deals
* similar rejected deals
* nearby distressed assets
* competing rental listings
* market absorption

Potential data sources:

* property data APIs
* broker reports
* public records
* MLS-like datasets where licensed
* local registries
* assessor data
* manual comp uploads
* scraped public listings where legally permitted

⸻

11. Monitoring and Alerts

The system should continuously monitor active deals, watchlist deals, and acquired assets.

Monitoring Feeds

For each deal:

* cash-flow actuals
* rent collections
* debt covenant compliance
* debt maturity
* construction budget
* construction progress
* construction timeline
* local permits
* zoning changes
* planning board agendas
* local news
* satellite imagery
* comparable sales
* comparable rents
* insurance costs
* tax reassessments
* sponsor updates
* tenant credit events
* legal deadlines
* document expirations
* capital call schedules

Alert Examples

Alert: DSCR projected below 1.20x in downside case.
Alert: Construction milestone missed by 30 days.
Alert: Local news reports opposition to nearby rezoning.
Alert: Comparable sale closed 12% below our exit assumption.
Alert: Sponsor has new litigation mention.
Alert: Satellite imagery shows no visible construction progress for 45 days.
Alert: Rent collections are 8% below budget for two consecutive months.
Alert: Debt maturity is within 180 days.
Alert: Insurance premium renewed 22% above budget.
Alert: Property tax reassessment materially exceeds underwriting.
Alert: New competing development announced within 1 mile.
Alert: Key tenant appears in bankruptcy-related news.
Alert: Actual NOI is 15% below acquisition underwriting.
Alert: Budget contingency is more than 70% consumed.

Alert Fields

Each alert should include:

* severity
* affected deal
* affected asset
* alert category
* source
* explanation
* financial impact
* recommended action
* owner
* due date
* status
* dismissed / resolved / escalated state

⸻

12. Main Screens

1. Portfolio Dashboard

Shows:

* current portfolio value
* equity invested
* realized gains
* unrealized gains
* IRR by asset
* equity multiple by asset
* exposure by geography
* exposure by asset type
* exposure by sponsor
* debt maturity schedule
* upcoming capital calls
* covenant watch
* top alerts
* actual vs underwritten performance
* cash-flow performance
* development progress

2. Deal Pipeline

Kanban-style pipeline:

New → Screening → Underwriting → IC → LOI → Diligence → Closed
                                   ↓
                                Rejected
                                   ↓
                                Watchlist

Each card should show:

* deal name
* asset type
* location
* price
* projected IRR
* projected equity multiple
* status
* owner
* top risk
* last update
* alert count

3. Deal Page

Tabs:

Overview
Documents
Extracted Facts
Financial Model
Scenarios
Comps
Map
News
Development Monitoring
Cash Flows
Risks
Alerts
Decision Log

4. Document Review Screen

Features:

* PDF viewer
* extracted facts panel
* confidence score
* source highlighting
* accept / reject / edit buttons
* page references
* extracted tables
* linked assumptions
* comments
* audit trail

5. Excel Model Viewer

Features:

* uploaded Excel preview
* mapped cells
* assumptions detected
* formulas detected
* broken formula warnings
* comparison against canonical model
* sponsor model vs internal model
* scenario export

6. Financial Model Screen

Features:

* sources and uses
* debt assumptions
* operating assumptions
* rent roll
* capex
* development budget
* exit assumptions
* returns
* sensitivities
* charts
* scenario comparison

7. Map and Market Screen

Features:

* property map
* satellite view
* parcel overlays
* nearby comps
* schools
* transit
* employment centers
* zoning
* permits
* local news pins
* nearby developments

8. Monitoring Center

Features:

* all alerts
* deadlines
* stale data feeds
* assets missing actuals
* current reforecasts
* construction delays
* cash-flow underperformance
* local events
* source health

9. Investment Committee Memo Generator

Auto-generate a draft memo with:

* deal summary
* investment thesis
* key risks
* property details
* sponsor details
* sources and uses
* debt terms
* projected returns
* scenario table
* sensitivity analysis
* comparable deals
* map
* local market context
* red flags
* recommendation

The generated memo should cite internal sources and require human approval.

⸻

13. Recommended Architecture

Do not build this as a purely local desktop application.

Use a server-backed architecture with a Windows-first desktop client and Android companion app.

Windows Desktop App
        │
Android Companion App
        │
Web/API Backend
        │
PostgreSQL + PostGIS
        │
Object Storage
        │
Document Extraction Workers
        │
Financial Analysis Engine
        │
Monitoring / Alert Engine
        │
External Data Connectors

Windows App

Recommended options:

* React + TypeScript
* WebView2 wrapper
* Tauri
* Electron

Best approach:

React + TypeScript frontend
FastAPI backend
Packaged for Windows using Tauri, Electron, or WebView2

Android App

Recommended options:

* React Native
* Flutter

Main mobile capabilities:

* push alerts
* deal summaries
* maps
* comments
* quick approvals
* document preview
* task updates
* watchlist review

Backend

Recommended stack:

FastAPI
Python workers
PostgreSQL
PostGIS
S3-compatible object storage
Redis or RabbitMQ
Temporal or Prefect
DuckDB
pandas
numpy-financial
scipy

Database

Use:

PostgreSQL + PostGIS

PostGIS is important because real estate is geospatial.

You will want queries like:

* all assets within 2 km of a transit station
* all deals near a flood zone
* all comps within 1 mile
* all assets affected by local news
* all properties near competing developments
* all rejected deals in a given market
* all assets in a specific zoning overlay

File Storage

Use object storage for:

* raw PDFs
* Excel files
* images
* satellite snapshots
* generated reports
* exports
* IC memos
* data-room files

Options:

* S3
* Azure Blob
* Google Cloud Storage
* MinIO for self-hosted storage

⸻

14. Data Model Sketch

Core tables:

deals
deal_status_history
assets
addresses
parcels
documents
document_pages
extracted_facts
fact_sources
spreadsheets
spreadsheet_cells
assumptions
scenarios
scenario_outputs
cash_flows_projected
cash_flows_actual
debt_terms
tenants
leases
rent_rolls
capex_items
development_budgets
development_milestones
market_comps
web_sources
news_events
imagery_snapshots
alerts
tasks
investment_decisions
audit_log

Example Tables

deals

id
name
status
asset_type
source
sponsor_id
broker_id
created_at
updated_at

assets

id
deal_id
address
city
state
country
latitude
longitude
parcel_id
asset_type
unit_count
building_size
land_size
year_built

assumptions

id
deal_id
scenario_id
category
name
value
unit
source_type
source_id
confidence
created_by
created_at

scenarios

id
deal_id
name
description
scenario_type
created_by
created_at
locked_at

alerts

id
deal_id
asset_id
severity
category
title
description
source
financial_impact
recommended_action
owner
due_date
status
created_at
resolved_at

⸻

15. AI Layer

Use AI for:

* document extraction
* prospectus summarization
* Excel model interpretation
* mapping extracted values to canonical fields
* detecting inconsistencies
* summarizing local news
* identifying risks
* classifying alerts
* comparing sponsor claims to external data
* drafting IC memos
* natural-language portfolio Q&A

Do not use AI as the source of truth for:

* financial calculations
* IRR
* NPV
* DSCR
* debt covenants
* legal conclusions
* final investment decisions
* unverified market comps

Use deterministic code for math.

Use AI for ingestion, explanation, summarization, and workflow acceleration.

⸻

16. Provenance and Audit Trail

Every important number should have a source.

Examples:

NOI: $1,200,000
Source: Offering Memorandum, page 14, table 2
Purchase price: $18,500,000
Source: Broker email, received 2026-06-12
Exit cap rate: 5.75%
Source: Analyst assumption, base case
Actual rent collections: $142,000
Source: May 2026 property management report

The system should track:

* who changed an assumption
* when it changed
* why it changed
* what scenario it affected
* whether an IC-approved case was modified
* which outputs changed as a result

⸻

17. Security and Permissions

Because this is for a family office, the system should support:

* user roles
* read-only users
* analyst users
* portfolio manager users
* admin users
* document-level permissions
* deal-level permissions
* audit logs
* encrypted file storage
* encrypted database fields for sensitive data
* SSO, if needed
* MFA
* backup and restore
* export controls
* data retention policies

Possible roles:

Admin
Portfolio Manager
Analyst
Principal
External Advisor
Read-Only Viewer

⸻

18. Reporting and Exports

The system should generate:

* IC memos
* deal summary PDFs
* portfolio reports
* asset-level monitoring reports
* monthly performance reports
* rejected-deal review reports
* cash-flow variance reports
* development progress reports
* lender covenant reports

Export formats:

* PDF
* Excel
* CSV
* PowerPoint
* Markdown
* JSON

⸻

19. MVP Build Plan

MVP 1: Deal Intake and Underwriting

Build first:

* create deal
* upload PDF
* upload Excel
* extract core fields
* review extracted facts
* normalize into canonical model
* run basic underwriting
* create base/downside/upside scenarios
* save deal state
* mark deal as rejected, watchlist, or acquired

This is the first useful product.

MVP 2: Web Enrichment

Add:

* geocoding
* map view
* satellite imagery
* local property data
* local news
* comparable sales
* comparable rents
* basic source tracking

MVP 3: Monitoring and Alerts

Add:

* scheduled monitoring jobs
* alert rules
* actual cash-flow imports
* construction milestone tracking
* local news alerts
* satellite imagery change review
* Android push notifications

MVP 4: Portfolio Intelligence

Add:

* cross-deal analytics
* rejected-deal hindsight analysis
* portfolio exposure maps
* IC memo generation
* actual vs underwritten analysis
* forecast vs actual learning loop
* natural-language portfolio questions

⸻

20. Recommended Implementation Stack

Frontend

React
TypeScript
TanStack Table
Mapbox or Google Maps
Recharts / ECharts
PDF.js
Handsontable or AG Grid

Windows Packaging

Tauri
Electron
or WebView2

Android

React Native
or Flutter

Backend

Python
FastAPI
Pydantic
SQLAlchemy
Celery / RQ / Dramatiq
Temporal or Prefect

Database

PostgreSQL
PostGIS
Redis
DuckDB

Financial Analysis

pandas
numpy
numpy-financial
scipy
openpyxl
xlwings if needed

Document Processing

Azure AI Document Intelligence
AWS Textract
Google Document AI
Tesseract for fallback OCR
LLM-based extraction with human review

Storage

S3
Azure Blob
Google Cloud Storage
MinIO

External Data

Google Maps Platform
Sentinel Hub
Planet
ATTOM
RentCast
GDELT
municipal GIS sources
planning board sources
public records
broker reports
manual CSV imports

⸻

21. Practical Build Priority

The most important part is not the map, the AI, or the charts.

The most important part is the canonical deal state model.

Everything else depends on it.

Priority order:

1. Deal model
2. Document and spreadsheet intake
3. Provenance system
4. Financial engine
5. Scenario engine
6. Deal status tracking
7. Web enrichment
8. Monitoring
9. Alerts
10. Portfolio intelligence
11. Android companion

⸻

22. Key Design Principles

1. Preserve All Deals

Do not delete rejected deals.

Rejected deals are valuable data.

2. Separate Facts From Assumptions

Facts, assumptions, and outputs must be separate.

3. Require Human Review

AI can propose. Humans approve.

4. Every Number Needs a Source

Every important number should be traceable.

5. Scenarios Must Be Versioned

The system should preserve how thinking changed over time.

6. Monitoring Is Part of the Product

The dashboard should not be static. It should actively watch the world.

7. Android Is for Action, Not Full Analysis

Use mobile for alerts, summaries, maps, approvals, and comments.

8. Build Provider Adapters

Do not hard-code the system around one real-estate data provider.

9. Use Deterministic Financial Math

Do not let LLMs calculate returns directly.

10. Make the Decision Log First-Class

The system should remember why a deal was accepted or rejected.

⸻

23. Final Recommended Architecture

Windows Desktop App
  React + TypeScript
  Tauri / Electron / WebView2
Android Companion App
  React Native or Flutter
Backend API
  FastAPI
  Python
  Pydantic
  SQLAlchemy
Database
  PostgreSQL
  PostGIS
Analytics
  pandas
  DuckDB
  numpy-financial
  scipy
Document Processing
  OCR
  table extraction
  LLM extraction
  human validation
Storage
  S3-compatible object storage
Workflow Engine
  Temporal or Prefect
Monitoring Engine
  scheduled jobs
  feed connectors
  alert rules
External Data
  maps
  satellite imagery
  property data
  local news
  public records
  local permits
  comparable deals

⸻

24. One-Sentence Summary

Build a Windows-first, server-backed real-estate deal operating system that ingests prospectuses and Excel models, extracts and verifies deal facts, runs deterministic financial analysis, enriches each deal with maps/news/comps/satellite data, preserves rejected deals for what-if analysis, continuously monitors active assets, and raises actionable alerts for a family office portfolio manager.
