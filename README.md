# Risk Discipline Assistant

> **Production-ready AI risk management platform that combines deterministic business rules with LLM-powered decision support.**

Unlike typical AI trading assistants, this system never delegates critical decisions to an LLM.

Instead, it combines a deterministic rule engine with multi-stage AI reasoning to create predictable, testable, and production-oriented workflows.

---

## Problem

Most AI trading assistants rely entirely on LLMs.

This creates several issues:

- unpredictable decisions
- hallucinations
- inconsistent recommendations
- difficult testing
- poor production reliability

For financial applications, business logic should remain deterministic.

---

## Solution

Risk Discipline Assistant separates deterministic validation from AI reasoning.

```
Trade Request
      │
      ▼
Deterministic Rule Engine
      │
      ▼
AI Risk Officer
      │
      ▼
AI Coach
      │
      ▼
Final Decision
```

Business rules always have the highest priority.

The AI layer never overrides deterministic validation.

Instead, it explains decisions, detects psychological bias, and provides contextual coaching.

---

## Engineering Highlights

- Designed deterministic rule engine with eight blocking risk rules.
- Built multi-stage AI decision pipeline.
- Integrated OpenAI, Anthropic and Ollama behind a provider abstraction.
- Implemented asynchronous FastAPI backend with PostgreSQL.
- Developed Telegram Bot and Flutter Web client.
- Added local-first AI deployment using Ollama.
- Implemented voice trade analysis with Whisper.
- Docker Compose deployment.
- CI-ready architecture.
- Modular service-oriented design.

---

# Why this architecture?

Large Language Models are excellent at reasoning, but they should not be responsible for enforcing critical business rules.

In financial software, deterministic validation must remain the source of truth.

For this reason, the application follows a layered decision architecture:

```
               Business Rules
                     │
                     ▼
         Deterministic Validation
                     │
                     ▼
            AI Risk Officer
                     │
                     ▼
               AI Coach
                     │
                     ▼
             Final User Feedback
```

Each layer has a clearly defined responsibility.

## Deterministic Rule Engine

Responsible for:

- stop-loss validation
- risk percentage
- leverage limits
- minimum Risk/Reward ratio
- daily loss protection
- consecutive loss protection
- emotional state validation
- revenge trading detection

These rules are fully deterministic and independently testable.

---

## AI Risk Officer

The Risk Officer performs contextual analysis after deterministic validation.

Its responsibilities include:

- identifying hidden risks
- reviewing trade quality
- evaluating trading discipline
- detecting inconsistent reasoning
- providing an additional approval layer

The Risk Officer can veto trades that satisfy deterministic rules but still exhibit unacceptable risk characteristics.

---

## AI Coach

Unlike the Risk Officer, the Coach never blocks a trade.

Instead, it explains:

- strengths of the setup
- weaknesses
- possible improvements
- psychological observations
- educational feedback

Separating coaching from validation keeps business logic predictable while still benefiting from LLM reasoning.

---

## Why not use AI for everything?

Many AI applications allow an LLM to become the primary decision-maker.

This project intentionally avoids that architecture.

Instead, AI is treated as an intelligent assistant rather than the source of truth.

This design improves:

- predictability
- reproducibility
- testing
- maintainability
- production reliability

- ---

# Architecture Decisions

This project was designed with production-oriented principles rather than simply integrating AI APIs.

Every major technology choice was made to improve maintainability, scalability and reliability.

---

## Why FastAPI?

FastAPI was selected because it provides:

- asynchronous request handling
- excellent typing support
- automatic OpenAPI documentation
- dependency injection
- high performance
- clean modular architecture

These characteristics make it well suited for AI backends that orchestrate multiple external providers.

---

## Why PostgreSQL?

Trading discipline generates structured, relational data.

PostgreSQL provides:

- ACID transactions
- reliable persistence
- strong indexing
- JSON support
- mature migration tooling

Unlike NoSQL databases, PostgreSQL guarantees consistency for user journals and trading history.

---

## Why Async SQLAlchemy?

The backend communicates with:

- Telegram
- AI providers
- PostgreSQL
- Signal Scanner

Using asynchronous SQLAlchemy allows these operations to run efficiently without blocking request processing.

---

## Why Ollama?

Most AI applications depend entirely on cloud APIs.

This project supports local inference through Ollama to provide:

- zero API costs
- improved privacy
- lower latency
- offline capability
- provider independence

Cloud providers remain optional rather than mandatory.

---

## Why Multiple AI Providers?

Different models have different strengths.

The provider abstraction allows switching between:

- OpenAI
- Anthropic
- Ollama

without changing the business logic.

This reduces vendor lock-in and makes experimentation significantly easier.

---

## Why Telegram?

Most traders already spend significant time inside Telegram.

Instead of building another standalone application, the system integrates directly into an existing workflow.

Reducing friction increases the probability that users actually follow their discipline process.

---

## Why Docker?

The complete development environment can be reproduced with a single command.

Docker provides:

- identical environments
- reproducible deployments
- simplified onboarding
- infrastructure portability

This significantly reduces deployment complexity.

---

## Why Service Separation?

The repository intentionally separates responsibilities into multiple services.

Each service has a single responsibility:

- Discipline Backend
- Telegram Bot
- Signal Scanner
- Flutter Dashboard

This architecture allows components to evolve independently while remaining loosely coupled.

---

# Engineering Challenges

Building AI applications is relatively easy.

Building reliable AI systems is significantly more difficult.

During development several engineering challenges had to be addressed.

---

## Challenge 1 — Preventing AI from becoming the source of truth

Many AI applications simply send a prompt to an LLM and trust the response.

This approach is unsuitable for financial applications where incorrect recommendations may lead to financial losses.

### Solution

The system validates every trade using deterministic business rules before AI analysis begins.

The LLM never executes business logic.

Instead it performs contextual reasoning on top of validated data.

---

## Challenge 2 — AI Provider Independence

Depending on a single provider creates multiple risks:

- pricing changes
- outages
- rate limits
- vendor lock-in

### Solution

The application introduces an abstraction layer that supports multiple providers:

- OpenAI
- Anthropic
- Ollama

Switching providers requires configuration changes rather than code changes.

---

## Challenge 3 — Local AI Support

Many users prefer not to send financial information to cloud providers.

### Solution

The system supports fully local inference through Ollama.

Users can deploy the complete application without relying on external AI services.

This improves privacy while eliminating API costs.

---

## Challenge 4 — Reducing User Friction

Long forms discourage traders from consistently following their discipline process.

### Solution

Voice messages are automatically transcribed using Whisper.

The extracted information pre-fills the trade validation workflow, reducing manual input and making discipline checks significantly faster.

---

## Challenge 5 — Separation of Responsibilities

Combining Telegram logic, AI orchestration, business rules and signal generation into a single service quickly becomes difficult to maintain.

### Solution

The project separates responsibilities into independent services:

- Telegram Bot
- Discipline Backend
- Signal Scanner
- Flutter Dashboard

Each service has a clearly defined responsibility and communicates over HTTP.

This architecture improves maintainability and simplifies future scaling.

---

# Engineering Trade-offs

Every architecture is a collection of trade-offs rather than perfect decisions.

Several deliberate compromises were made during development.

---

## Rule Engine before AI

### Pros

- predictable
- testable
- deterministic
- easy to debug

### Cons

- less flexible
- requires manual rule maintenance

The increased reliability outweighs the additional maintenance cost.

---

## Local AI Support

### Pros

- privacy
- zero API costs
- offline capability

### Cons

- slower inference
- hardware requirements

Cloud providers remain available for users prioritizing speed.

---

## Multiple Services

### Pros

- clear separation of concerns
- easier maintenance
- better scalability

### Cons

- more deployment complexity
- additional infrastructure

The modular architecture is better suited for long-term evolution than a monolithic application.

---

## Multiple AI Providers

### Pros

- avoids vendor lock-in
- easier experimentation
- improved reliability

### Cons

- additional abstraction layer
- more integration testing

The flexibility gained outweighs the small implementation complexity.

---

# Performance & Scalability

Although the project is primarily designed as a personal discipline platform, the architecture allows future scaling with minimal changes.

## Current Architecture

The current implementation supports:

- asynchronous request processing
- modular service separation
- provider abstraction
- independent AI backends
- isolated frontend and backend applications

This makes horizontal scaling significantly easier than tightly coupled monolithic solutions.

---

## Scaling Strategy

As user traffic increases, the architecture can evolve incrementally.

### API Layer

Multiple FastAPI instances behind a reverse proxy.

```
Users
   │
   ▼
NGINX
   │
 ┌─┴────────────┐
 │              │
 ▼              ▼
FastAPI      FastAPI
 │              │
 └──────┬───────┘
        ▼
   PostgreSQL
```

---

### Background Processing

Long-running AI operations can be moved into background workers.

Examples:

- AI reviews
- market scanning
- weekly reports
- voice transcription
- notifications

This prevents API requests from blocking user interactions.

Potential technologies:

- Celery
- Redis
- RabbitMQ

---

### Database Scaling

The application currently uses PostgreSQL as the primary datastore.

Future improvements may include:

- read replicas
- connection pooling
- caching
- query optimization

without requiring changes to business logic.

---

### AI Scaling

The provider abstraction allows distributing requests across multiple models.

Example:

- OpenAI for reasoning
- Ollama for local inference
- Anthropic for deep analysis

Each provider can be enabled or disabled through configuration.

---

# Production Readiness

The project was designed with production deployment in mind.

## Already Implemented

- Docker Compose deployment
- environment-based configuration
- database migrations
- asynchronous backend
- modular architecture
- CI tests
- provider abstraction
- local AI deployment
- API documentation
- isolated frontend/backend

---

## Planned Improvements

- Redis caching
- Celery task queue
- JWT authentication
- Prometheus metrics
- Grafana dashboards
- rate limiting
- centralized logging
- Kubernetes deployment
- distributed tracing
- object storage

- ---

# Engineering Philosophy

The primary goal of this project was never to build another AI chatbot.

Instead, the objective was to design a reliable AI system where deterministic business logic and language models complement each other.

Several engineering principles guided the implementation.

## AI should assist, not control.

Business rules remain deterministic.

LLMs provide reasoning rather than authority.

---

## Simplicity over complexity.

Each service has a clearly defined responsibility.

The architecture favors maintainability over unnecessary abstraction.

---

## Provider independence.

No business logic depends on a specific AI vendor.

Cloud and local inference are interchangeable.

---

## Production-first thinking.

Every architectural decision considers:

- maintainability
- scalability
- testing
- deployment
- long-term evolution

- ---

# Lessons Learned

Building this project reinforced several important engineering principles.

- LLMs should complement deterministic systems rather than replace them.
- Modular architectures simplify long-term development.
- AI provider abstraction greatly improves flexibility.
- Local AI is becoming increasingly practical for production workloads.
- Separating business logic from AI significantly improves reliability.
- Good developer experience accelerates future development more than clever code.

- ---

# About the Author

Hi, I'm **Raian Bagautdinov**.

I'm an Applied AI Engineer focused on designing production-ready AI systems using FastAPI, PostgreSQL, LLMs, RAG and local AI.

My primary interest is building AI applications that combine deterministic software engineering with modern language models to create reliable and maintainable systems.

I enjoy designing architectures where AI enhances decision-making without becoming the source of truth.
