# API Layer Module (`src/api_layer`)

## Purpose
Exposes public external endpoints via REST, real-time bidirectional WebSocket gateways, and gRPC stubs. Handles incoming request routing, rate limiting, and response serialization.

## Architectural Layer
**Interface Adapter Layer (SRP)**. Decoupled from core business logic, converting wire format payloads into internal domain models.

## Subdirectories
- `rest/`: FastAPI controllers and HTTP route handlers.
- `websocket/`: Real-time streaming gateway for low-latency audio & agent event loops.
- `grpc/`: High-performance microservice RPC stubs.
- `middleware/`: Authentication, rate limiting, exception transformation, CORS.
