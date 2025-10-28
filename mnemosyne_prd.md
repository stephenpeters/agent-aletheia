Mnemosyne System – Product Requirements Document (PRD)

This PRD outlines the vision, architecture, and detailed requirements for each Mnemosyne agent and shared module.

⸻

1. Overview

Purpose: Mnemosyne is a modular AI content system that automates idea discovery, drafting, refinement, and publication while maintaining an authentic human voice. The platform comprises four main agents — Aletheia, IRIS, Erebus, and Kairos — all governed by the Mnemosyne meta-layer for memory, learning, and style consistency.

Workflow:

Aletheia → IRIS → Erebus → Kairos
            ↑          ↓
          Mnemosyne (Memory & Governance)


⸻

2. Aletheia – Idea Discovery Agent

Mission: Identify, evaluate, and summarize potential content ideas from structured and unstructured data sources.

Core Capabilities
	•	Ingest URLs, RSS feeds, PDFs, and YouTube transcripts.
	•	Summarize articles into concise briefs.
	•	Score ideas by novelty, topicality, and relevance.
	•	Detect trends and cluster related ideas.

Key Deliverables
	•	aletheia.md documentation and JSON schemas.
	•	FastAPI service (/v1/ingest, /v1/ideas/generate, /v1/ideas/{id}).
	•	idea.json schema defining standardized idea format.

Dependencies
	•	Python 3.11, FastAPI, LangChain or Anthropic SDK for summarization.
	•	Postgres + pgvector for idea embeddings.
	•	Integration with Mnemosyne context API for relevance checks.

⸻

3. IRIS – Drafting & Composition Agent

Mission: Generate structured outlines and high-quality drafts in the author’s authentic tone.

Core Capabilities
	•	Transform Aletheia briefs into structured outlines (Define → Contrast → Synthesize → Project).
	•	Apply VoicePrint parameters to preserve cadence, rhythm, and diction.
	•	Generate drafts with voice and stylistic metrics.
	•	Output in markdown or plain text for Notion synchronization.

Key Deliverables
	•	iris.md documentation, prompt templates, and voiceprint.json.
	•	FastAPI endpoints: /v1/outlines, /v1/drafts, /v1/drafts/{id}.

Dependencies
	•	Anthropic SDK (for draft generation) and optional OpenAI cross-checking.
	•	Shared SDK for schemas and logging.

⸻

4. Erebus – Authenticity & Post-Processing Agent

Mission: Remove detectable AI fingerprints and reintroduce human irregularity while retaining meaning.

Core Capabilities
	•	Detect AI-generated patterns using ensemble classifiers.
	•	Apply linguistic perturbations (clause deformation, rhythm irregularity, entropy injection).
	•	Generate differential reports (diff_summary) to track text changes.
	•	Output AI-likelihood and voice deviation metrics.

Key Deliverables
	•	erebus.md documentation and cleaned.json schema.
	•	Endpoint: /v1/clean for draft refinement.

Dependencies
	•	OpenAI or custom heuristic-based detector.
	•	Access to Mnemosyne for stylistic baseline comparison.

⸻

5. Kairos – Scheduler & Publishing Agent

Mission: Schedule, post, and analyze content performance to optimize engagement timing.

Core Capabilities
	•	Interface with LinkedIn API to publish approved posts.
	•	Determine optimal timing windows based on engagement history.
	•	Log publish metadata and retrieve analytics.
	•	Feed performance data back into Mnemosyne.

Key Deliverables
	•	kairos.md documentation and publish.json schema.
	•	Endpoints: /v1/schedule, /v1/posts/{id}.
	•	Integration with n8n workflows and Notion approvals.

Dependencies
	•	LinkedIn API, Redis or Postgres for queueing.
	•	Mnemosyne analytics interface.

⸻

6. Mnemosyne – Memory & Governance Layer

Mission: Maintain cross-agent memory, track voice drift, and enforce governance rules for data and tone consistency.

Core Capabilities
	•	Persist embeddings of all generated and published content.
	•	Serve contextual data for new drafts and ideas.
	•	Monitor voice deviation and topic balance.
	•	Manage keys, credentials, and access scopes.

Key Deliverables
	•	mnemosyne.md documentation and mnemosyne_corpus schema.
	•	API endpoints: /v1/context, /v1/learn.

Dependencies
	•	Postgres + pgvector, cloud storage for long-term content archives.
	•	Cloud KMS + Secret Manager for key control.

⸻

7. Shared SDK & Infrastructure

Mission: Provide shared schemas, data models, clients, and DevOps configuration.

Components
	•	agent-sdk: JSON schemas, Python/TypeScript clients, logging utilities.
	•	infra: Terraform configurations, n8n flows, and Docker templates.
	•	Standard event envelope for all agents.

Shared Schema Example

{
  "type": "idea.created|outline.ready|draft.cleaned|publish.scheduled",
  "id": "uuid",
  "time": "timestamp",
  "actor": "agent-name",
  "data_ref": "s3://bucket/key",
  "meta": {}
}


⸻

8. Technical Architecture

Layer	Technology	Purpose
API	FastAPI	Lightweight, async microservices
Data	Postgres + pgvector	Relational data + semantic search
Storage	S3-compatible	Versioned text and media blobs
Messaging	AWS SQS / Pub/Sub	Event-driven agent communication
Workflow	n8n	Visual orchestration & scheduling
Auth	JWT + Secret Manager	Secure inter-agent auth


⸻

9. Development Model

Repository Structure

Each agent/module lives in a separate GitHub repo for isolation, permissions, and CI/CD independence:

mnemosyne-aletheia
mnemosyne-iris
mnemosyne-erebus
mnemosyne-kairos
mnemosyne-mnemosyne
mnemosyne-sdk
mnemosyne-infra

Environment
	•	macOS or Linux preferred.
	•	VS Code multi-root workspace.
	•	Python 3.11 virtualenv per agent.
	•	CI/CD: GitHub Actions (lint, test, build, deploy).

⸻

10. Phases & Milestones

Phase	Deliverables	Description
Phase 1 – MVP	Aletheia + IRIS	Manual review loop with Notion integration.
Phase 2 – Automation	Add Erebus + Kairos	Full autonomous pipeline with human approval.
Phase 3 – Intelligence	Mnemosyne	Adaptive learning and voice drift control.
Phase 4 – Scale	Monitoring & Governance	Analytics dashboard and multi-user support.


⸻

11. KPIs & Success Metrics

Metric	Target
Draft-to-publish latency	< 24h
Human edit distance	< 20%
AI-likelihood after Erebus	< 0.25
Voice deviation	< 0.35
Post approval rate	> 90%
System uptime	99.9%


⸻

12. Governance & Compliance
	•	Monthly key rotation; role-based secrets.
	•	Audit trail of all transformations per post.
	•	Optional human approval checkpoint.
	•	Mnemosyne corpus encrypted at rest and in transit.

⸻

13. Deliverables Summary
	•	Agent Artefacts: aletheia.md, iris.md, erebus.md, kairos.md, mnemosyne.md, shared.md.
	•	Setup Guide: setup_instructions.md + bootstrap_mnemosyne.sh.
	•	Infrastructure Repo: Terraform + n8n workflows.
	•	Developer Docs: SDK usage, schema references, and local dev instructions.

⸻

Outcome: A modular, scalable system for human-authentic content creation — architected for reliability, security, and continuous learning.
