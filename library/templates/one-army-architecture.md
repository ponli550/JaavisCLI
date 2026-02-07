# One-Army System Architecture Template

This document serves as the master reference for a "Grand Unified Architecture" designed for a single developer ("One-Army") to deploy, maintain, and scale a complex ecosystem spanning **Mobile, Web, IoT, AI, and Cybersecurity**.

> **Philosophy**: Maximum Automation, Monolithic Repo, Modular Services.

---

## 1. High-Level Tech Stack (The "One-Army" Stack)

### **Core**
- **Repo Strategy**: Monorepo (Turborepo / Nx) - Share types, UI, and logic everywhere.
- **Language**: TypeScript (Frontend/API) + Python (AI/Data) + Rust/C++ (IoT/Edge).
- **Database**: Supabase (PostgreSQL + pgvector).
    - *Why?* Unified "Glass Box" architecture. Relational data and AI Embeddings live in one SQL-queryable platform.
    - *Component*: Redis (Cache).

### **Domains**
| Domain | Primary Tech | Reserved Slot |
| :--- | :--- | :--- |
| **Frontend (Web)** | React (Vite/Next.js), Tailwind CSS | `[RESERVED: FUTURE WEB TECH]` |
| **Frontend (Mobile)** | React Native (Expo), NativeWind | `[RESERVED: FUTURE MOBILE TECH]` |
| **Backend (API)** | Node.js (Hono/Fastify) or Go | `[RESERVED: FUTURE API TECH]` |
| **IoT & Edge** | ESP32 (C++), Raspberry Pi (Python/Rust), MQTT | `[RESERVED: FUTURE IOT PROTOCOL]` |
| **AI & ML** | PyTorch, LangChain, Ollama/OpenAI | `[RESERVED: FUTURE MODEL ARCH]` |
| **DevOps** | Docker, K8s (k3s) or Coolify, Terraform | `[RESERVED: FUTURE INFRA TECH]` |

---

## 2. Monorepo Directory Structure

```
root/
├── apps/
│   ├── web-client/           # Consumer facing web app
│   ├── web-admin/            # Central Command Dashboard (God Mode)
│   ├── mobile-app/           # iOS/Android Universal App
│   └── api-server/           # Main Gateway / GraphQL Federation
│
├── packages/
│   ├── ui-kit/               # Universal Design System (Web + Mobile)
│   ├── core-types/           # Shared Zod schemas & TS interfaces
│   ├── lib-iot/              # Shared IoT decoders & MQTT handlers
│   └── lib-ai/               # Shared prompt templates & logic
│
├── services/                 # Microservices (if separated from api-server)
│   ├── ai-agent-worker/      # Background Job Runner (Python)
│   ├── iot-ingestor/         # High-throughput MQTT Consumer (Rust/Go)
│   └── cron-scheduler/       # Temporal/Agenda tasks
│
├── firmwares/                # Embedded Code
│   ├── sensor-node-v1/       # ESP32 Code
│   └── edge-gateway/         # Raspberry Pi Local Intelligence
│
└── infra/                    # DevOps as Code
    ├── docker/               # Compose files for dev
    ├── k8s/                  # Helm charts / Manifests
    └── terraform/            # Cloud provisioning
```

---

## 3. Domain Architectures

### A. Frontend (Web & Mobile)
**Goal**: Write once, adapt everywhere.
- **State**: Global Store (Zustand) synchronized via WebSockets/Sync Engine (WatermelonDB).
- **UI**: "Neo-Glass / Futuristic" - Deep blurs, noise textures, and motion-heavy.
- **Micro-interactions**: Mandatory haptic/visual feedback for *all* user actions.
- **`[RESERVED FOR FUTURE FRONTEND PATTERN]`**

### B. Backend & API Layer
**Goal**: Type-safe contract between all client apps.
- **Protocol**: tRPC (for TypeScript mono-stack) or GraphQL (for broader compatibility).
- **Auth**: Centralized Identity Provider (Keycloak / Auth0 / Supabase).
- **`[RESERVED FOR FUTURE BACKEND PATTERN]`**

### C. IoT & Edge Computing
**Goal**: Robust telemetry handling even with unstable connection.
1.  **Devices**: Publish to local or cloud MQTT Broker.
2.  **Edge Gateway**: Pre-process data (cleaning/compression) before sending to cloud.
3.  **Digital Twin**: Cloud DB mirrors device state for offline access.
4.  **`[RESERVED FOR FUTURE IOT STRATEGY]`**

### D. Artificial Intelligence (AI) & ML
**Goal**: AI as a coworker, not just a chatbot.
1.  **Agentic Workflow**: "CrewAI" style agents (Researcher, Coder, Reviewer) running in background.
2.  **RAG Pipeline**: Ingest documentation/logs -> Vector Store connection -> LLM Context.
3.  **Vision**: On-premise Object Detection (YOLO/Ollama) for security feeds.
4.  **Memory ("The Glass Box")**:
    - **Strategy**: Use `pgvector` in Supabase.
    - **Observability**: Inspect "AI Thoughts" directly via SQL tables (`SELECT * FROM memories`). No black-box vector silos.
    - **`[RESERVED FOR FUTURE AI PIPELINE]`**

---

## 4. Cybersecurity Mesh

**Security is not an afterthought.**

*   **Zero Trust**: Mutual TLS (mTLS) between services.
*   **Edge Security**: Device Identity Certificates (X.509) for IoT nodes.
*   **Data Sovereignty**: Sensitive data encrypted at rest and in transit.
*   **AI Guardrails**: Input sanitization to prevent Prompt Injection.
*   **`[RESERVED FOR FUTURE SEC PROTOCOL]`**

---

## 5. Implementation Roadmap (The "One-Army" Workflow)

### Phase 1: Foundation
1.  Setup Monorepo & CI/CD Pipelines (GitHub Actions).
2.  Deploy centralized DB & Auth.
3.  Establish "Hello World" on Web, Mobile, and API.

### Phase 2: Core Business Logic
1.  Implement main CRUD features.
2.  Connect Real-time Websockets.
3.  **`[RESERVED FOR PHASE 2 EXPANSION]`**

### Phase 3: The "Senses" (IoT & Vision)
1.  Flash firmwares to devices.
2.  Visualize telemetry on Admin Dashboard.
3.  Setup Alerts/Triggers based on sensor data.

### Phase 4: The "Brain" (AI Layer)
1.  Deploy Vector DB.
2.  Train/Fine-tune models on proprietary data.
3.  Activate proactive AI Agents.

---

## 6. Automation & DevOps

For a single developer, **Automation is King**.
*   **Visual Testing**: Chromatic / Percy for UI regression.
*   **Deployment**: Push-to-deploy (Vercel/Railway/Coolify).
*   **Monitoring**: GlitchTip / Sentry for error tracking.
*   **`[RESERVED FOR FUTURE AUTOMATION]`**

---

## 7. Visual Style & "Best UX" Standards

**Aesthetic Goal: "Sci-Fi Realism" (Neo-Glass)**

### A. The "Neo-Glass" Definition
- **Depth**: Interface must feel volumetric. Use 3 layers:
    1.  *Base*: Dark, grainy gradients (Noise opacity 5%).
    2.  *Glass*: `backdrop-filter: blur(20px)` + `saturate(180%)`.
    3.  *Highlight*: 1px Inner Borders (`border-white/10`) to simulate edge lighting.
- **Lighting**: Use radial gradients to simulate "glows" behind active elements.
- **Typography**:
    - *Headers*: Geometric Sans (Inter/Roobert).
    - *Data/Technical*: Monospace (JetBrains Mono) with `tracking-wider`.

### B. Interaction Design ("Best UX")
- **The "No-Dead" Rule**: Every click, hover, or focus MUST trigger a response.
    - *Hover*: Scale up (1.02x) or Glow increase.
    - *Active*: Scale down (0.98x) or Ripple effect.
- **Transitions**:
    - *Page*: No hard cuts. Use `<AnimatePresence>` for cross-dissolve or slide.
    - *Layout*: Shared Layout Animations (`framer-motion`) when lists re-order.
- **Loading States**:
    - **Never** use simple spinners for main content.
    - **Always** use "Shimmering Skeletons" that match the glass opacity.

---

## 8. Business & Monetization Layer

**Code is Liability, Revenue is Asset.**

### A. Payments & Billing
- **Provider**: Stripe (Custom Flow) or LemonSqueezy (Merchant of Record).
- **Webhooks**: Dedicated microservice to handle asynchronous payment events.
- **`[RESERVED FOR FUTURE PAYMENT PROVIDER]`**

### B. Product Analytics
- **Unified Tracking**: PostHog (Session Replay + Events).
- **Goal**: Understand *who* is using features, not just *that* they are used.
- **`[RESERVED FOR FUTURE ANALYTICS]`**

### C. Customer Support
- **Embedded**: Chatwoot or Intercom connected to Slack/Discord for instant reply.
- **`[RESERVED FOR FUTURE SUPPORT CHANNEL]`**

---

## 8. Operational Continuity

**The "Bus Factor" Fix.**

### A. Automated Backups
- **Database**: Daily dumps to S3/R2 with lifecycle rules (30-day retention).
- **Code**: GitHub/GitLab mirror.
- **`[RESERVED FOR FUTURE BACKUP STRATEGY]`**

### B. Health & Uptime
- **External Monitoring**: BetterStack or Uptime Kuma.
- **Alerting**: PagerDuty or simple Discord Webhook.
- **`[RESERVED FOR FUTURE MONITORING]`**

### C. Documentation as Code
- **Engine**: Starlight (Astro) or Docusaurus in `/apps/docs`.
- **Content**: Architecture Decision Records (ADRs) stored next to code.
- **`[RESERVED FOR FUTURE DOCS PLATFORM]`**

---

## 9. Force Multipliers (Tooling Strategy)

**Buy Time, Don't Build It.**

### A. SaaS vs. Build
- **Auth**: Buy (Clerk/Auth0) unless >100k MAU.
- **Email**: Buy (Resend/SendGrid).
- **Search**: Buy (Algolia/Meilisearch Cloud).

### B. Generators & Scaffolders
- **Tool**: `plop.js` or `hygen`.
- **Use Case**: `yarn gen component MyButton` -> creates Component, Test, Story, Styles.

### C. AI Coding Standards
- **Rule**: All repos must have `.cursorrules` or `.github/copilot-instructions.md`.
- **Context**: Explicitly define tech stack preferences for the AI to reduce hallucination.

---

## 10. Industry Integration Standards (The "Glue")

**How to make it scalable, resilient, and compliant.**

### A. Event Mesh (The Nervous System)
- **Technology**: NATS.io (Lightweight) or Redpanda (Kafka-compatible).
- **Pattern**: Decouple services. IoT devices publish to the Mesh; AI subscribes to relevant topics.
- **`[RESERVED FOR FUTURE EVENT BROKER]`**

### B. Observability (OpenTelemetry)
- **Standard**: OTLP (OpenTelemetry Protocol).
- **Implementation**: Trace requests from Mobile App -> API -> Microservice -> DB.
- **Tools**: Jaeger (Tracing) + Prometheus (Metrics) + Grafana (Dashboard).
- **`[RESERVED FOR FUTURE OBSERVABILITY STACK]`**

### C. Container Orchestration
- **Production**: Kubernetes (k8s) is the industry standard.
- **One-Army Adaption**: Use `k3s` (lightweight distro) or managed services (DigitalOcean App Platform) to avoid ops fatigue.
- **`[RESERVED FOR FUTURE ORCHESTRATION]`**

---

## 11. Future Tech Radar (The KIV Log)

**Keep In View (KIV): Technologies to watch, strictly categorized.**

| Domain | Technnology | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Example** | *Bun Runtime* | `Assess` | *Fast start, but wait for stability.* |
| **Example** | *Quantum Safe Crypto* | `Hold` | *Not currently needed for MVP.* |

### Status Definitions
- **`Assess`**: Interesting. Read about it during downtime.
- **`Trial`**: Ready for a side-project or non-critical module.
- **`Hold`**: Irrelevant for now (too early / overkill).
- **`Adopt`**: Move to Main Stack in next refactor.

**`[RESERVED FOR FUTURE KIV ITEMS]`**

---

## 12. Project Grading & Standards Matrix

> **MANDATORY DAY 0 QUESTION**: Before writing a single line of code, you MUST classify the project into one of these three grades. This decision dictates the strictness of your standards.

| Feature | **Grade C (Skirmish)** | **Grade B (Campaign)** | **Grade A (Fortress)** |
| :--- | :--- | :--- | :--- |
| **Typical Use Case** |  OC / MVP / Hackathon | Internal Tool / Standard SaaS | Enterprise / Fintech / Health |
| **Speed vs. Quality** | Speed First | Balanced | Quality First |
| **File Storage** | Public Local Disk | Cloud (S3/Spaces) | **Gold Standard** (Secure, Partitioned, CDN) |
| **Auth** | Basic (Email/Pass) | OAuth + Teams | MFA + RBAC + Audit Logs |
| **Database** | SQLite / Local Postgres | Managed DB (Supabase) | Checksums, Encrypted Columns, Read Replicas |
| **Testing** | Manual Only | Unit Tests (Critical Paths) | 100% Coverage + E2E |
| **Infrastructure** | `npm run start` / Screen | Docker Compose | K8s / High Availability |
| **Documentation** | README.md only | Context Docs (`.cursorrules`) | Full Architecture Decision Records (ADR) |

**Adoption Rules:**
*   **Grade C**: Allowed to break "One-Army" rules for speed. Tech debt is expected.
*   **Grade B**: The default. Follows `TEMPLATE_FRONT_ARCHITECTURE3.md`.
*   **Grade A**: Must follow `LARAVEL_SECURE_FILE_UPLOAD_STANDARD.md` and other "Gold Standard" protocols strictly.

