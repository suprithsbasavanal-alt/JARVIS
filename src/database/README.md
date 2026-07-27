# Database Module (`src/database`)

## Purpose
Manages relational storage persistence, ORM models, vector database connections, Redis caching, and database migrations.

## Architectural Layer
**Infrastructure & Driver Layer**. Implements generic repository ports (Repository Pattern & Unit of Work) defined in `contracts/`.

## Subdirectories
- `contracts/`: Abstract Base Classes for generic repositories (`BaseRepository`, `UnitOfWorkContract`).
- `relational/`: SQLAlchemy ORM / AsyncPG models and Alembic migrations.
- `vector/`: Qdrant / Chroma vector store adapters.
- `cache/`: Redis key-value cache client wrapper.
