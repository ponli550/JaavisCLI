# Advanced AI Entity Relationship Diagram (ERD)

This document outlines the proposed target architecture for the JAAVIS platform, incorporating advanced AI workflows, vector search capabilities, and transparent reasoning logs.

## Target Architecture Model

```mermaid
erDiagram
    %% CORE RELATIONSHIPS
    USER ||--o{ CHAT-SESSION : "initiates"
    USER ||--o{ BID : "submits"
    TENDER ||--o{ BID : "receives"
    TENDER ||--o{ DOCUMENT : "has source files"
    BID ||--o{ DOCUMENT : "has attachments"

    %% AI WORKFLOW RELATIONSHIPS
    TENDER ||--o| AI-JOB : "triggers (Ingestion)"
    BID ||--o| AI-JOB : "triggers (Evaluation)"
    DOCUMENT ||--o| VECTOR-EMBEDDING : "indexed as"
    AI-JOB ||--o{ AI-LOG : "generates reasoning"

    USER {
        string email PK
        string role
        string company
    }

    TENDER {
        objectId id PK
        string title
        string scope
        number budget
        string status
        objectId vectorId FK "Ref: Vector Store"
    }

    BID {
        objectId id PK
        objectId tenderId FK
        number amount
        number aiScore
        string scoreLabel
        string scoreReasoning "AI generated feedback"
        string status
    }

    DOCUMENT {
        objectId id PK
        string url
        string contentHash
        string textContent "Extracted via OCR"
    }

    %% NEW AI ENTITIES
    AI-JOB {
        objectId id PK
        string targetType "TENDER | BID"
        objectId targetId FK
        string agentType "ANALYST | EVALUATOR"
        string status "QUEUED | PROCESSING | COMPLETED | FAILED"
        date startedAt
        date completedAt
    }

    AI-LOG {
        objectId id PK
        objectId jobId FK
        string step "Processing Step Name"
        string thoughtProcess "Chain of Thought"
        json metadata "Confidence Scores/Tokens"
    }

    VECTOR-EMBEDDING {
        objectId id PK
        objectId documentId FK
        vector embedding "1536-dim array"
        string chunkText
        json metadata "Page #, Source"
    }

    CHAT-SESSION {
        objectId id PK
        objectId userId FK
        array messages
        string contextScope "Tender-Specific | General"
    }
```

---

## Architectural Highlights

### 1. AI Processing Pipeline (`AI-JOB` & `AI-LOG`)
- **Asynchronous Execution**: Tender ingestion and Bid evaluation are handled as background jobs to ensure UI responsiveness.
- **Transparency**: The `AI-LOG` entity captures the "Chain of Thought," allowing users to see exactly how the AI arrived at a specific score or suggestion.

### 2. Vector Search Infrastructure (`VECTOR-EMBEDDING`)
- **RAG Capability**: Documents are chunked and embedded into a high-dimensional vector space (e.g., Pinecone or pgvector).
- **Semantice Search**: The `vectorId` in the `TENDER` model enables fast, context-aware retrieval of relevant construction codes and requirements.

### 3. Integrated Feedback Loop
- **Evaluation Reasoning**: Use `scoreReasoning` in the `BID` model to provide actionable feedback to subcontractors based on the matching results from the Evaluator agents.
