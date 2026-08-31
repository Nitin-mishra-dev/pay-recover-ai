# PAYRECOVER AI — ENGINEERING QUALITY STANDARD

## Before Coding

Inspect:
- repository structure
- package manager
- runtime
- existing tests
- configuration
- database
- docs

Do not rewrite infrastructure without necessity.
Prefer the existing project stack; standardize only when the architecture decision explicitly chooses it.

## Backend Guidelines

When building or extending backend services:
- Prefer clean, typed service boundaries (e.g. FastAPI / Pydantic in Python).
- Explicit database schema and migration discipline (e.g. PostgreSQL / SQLite for lightweight test environments).
- Explicit transaction boundaries and atomic operations for state changes.
- Pure functions for business calculations (e.g. ENIV math) decoupled from I/O.

## Frontend Guidelines

When building user interfaces:
- Prioritize clear information hierarchy and decision clarity.
- Explicit loading, error, and empty states.
- Deterministic data rendering matching backend API contracts.
- No decorative fake AI fluff.

## API Contracts

Every mutation must define:
- strict input validation
- authorization & safety checks
- idempotency handling
- typed response schema
- structured error codes

## Tests

Each feature requires appropriate:
- unit tests for business logic and schemas
- integration tests for API endpoints and database operations
- failure-path and edge-case tests
- state-transition tests and race-condition tests

## Observability & Telemetry

Errors and logs should include enough structured context to debug:
- request/event id
- payment id
- recovery case id
- action id
- state
- failure reason
- runtime safety telemetry counters

## Changes

Keep diffs narrow.

Do not mix:
- refactors
- features
- dependency migrations
- formatting
into one change unless strictly necessary.
