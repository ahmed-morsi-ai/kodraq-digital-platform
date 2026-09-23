# Kodraq Digital Operating Platform

Kodraq Digital is a unified enterprise operating platform that bridges technical training, talent assessment, intelligent workforce orchestration, and B2B client operations. The system is engineered with strict domain isolation and deterministic workflows, ensuring a seamless transition from student evaluation to corporate project delivery.

## System Architecture

The platform follows a decoupled, service-oriented architecture:

* **Backend Services:** Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic, Redis.
* **Frontend Application:** React, Vite, TypeScript, Tailwind CSS v4, strictly typed and modularized.
* **Storage & AI Infrastructure:** Cloudflare R2 for object storage, OpenAI/Local AI Gateway for deterministic copilot operations, and pgvector for track-scoped Retrieval-Augmented Generation (RAG).

## Core Domains

1. **Academy & Assessment:** Paid technical tracks, deterministic enrollment logic, immutable quiz attempts, server-side anti-cheat enforcement, and algorithmic graduation gates.
2. **Talent & Workforce:** Skills matrix, performance tracking, and automated candidate pooling based on quantitative training metrics.
3. **CRM & Client Portal:** Service catalog, AI-assisted requirement extraction, automated pricing engines, and secure client-facing project visibility.
4. **Project Orchestration:** Task state machines, RBAC-protected employee workspaces, GitHub integration, and mandatory QA checkpoints.

## Engineering Standards & Quality Assurance

This repository is maintained under absolute technical rigor. The following policies are enforced programmatically:

* **Zero Technical Debt Policy:** No feature is considered complete without passing 100% of its automated test suite.
* **Mandatory Terminal Evidence:** Commits are blocked unless `pytest` yields a zero exit code and `ruff` reports zero linting violations.
* **State Machine Integrity:** All entities (Submissions, Quizzes, Projects) rely on backend-enforced state transitions. Client-side state manipulation is systematically rejected.
* **Security & Isolation:** Role-Based Access Control (RBAC) is enforced at the router and ORM level. Data leaks between tracks, students, or clients are prevented via strict ownership validation logic.

## Deployment & Environments

The application is containerized using Docker and managed via Docker Compose for parity across local, staging, and production environments. Database migrations are exclusively managed through Alembic branch-less graphs.

---
*Kodraq Digital Core Engineering*
