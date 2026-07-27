# Memory Module (`src/memory`)

## Purpose
Manages multi-tiered contextual memory for the assistant, including short-term conversation context, long-term vector semantic embeddings (RAG), working memory scratchpads, and dynamic knowledge graphs.

## Architectural Layer
**Domain Abstraction & Data Access Layer**. `src/memory/contracts/` defines fine-grained interfaces (ISP) for memory storage backends.

## Subdirectories
- `contracts/`: Abstract Base Classes for memory stores (`BaseMemoryStore`, `VectorStoreContract`).
- `short_term/`: Session context window sliding buffer and immediate dialogue context.
- `long_term/`: RAG semantic index, dense embedding retrieval, and vector storage integration.
- `working_memory/`: Active task execution state scratchpad.
