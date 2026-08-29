# Container View

"Container" here follows the C4 meaning: a separately runnable application or
data store, not necessarily a Docker container.

```mermaid
flowchart TB
    subgraph Clients
      Web[Next.js web\nReact 18]
      Mobile[Expo app\nReact Native / React 19]
    end
    Shared[Shared schemas\n@medical/shared]
    Client[Shared HTTP client\n@medical/api-client]
    API[FastAPI modular monolith]
    DB[(PostgreSQL + pgvector)]
    Pipeline[Python ingestion scripts]
    Google[Google OpenID Connect]

    Web --> Shared
    Web --> Client
    Mobile --> Shared
    Mobile --> Client
    Client -->|JSON/HTTPS| API
    API --> DB
    Pipeline --> DB
    Web --> Google
    Mobile --> Google
    API -->|verify ID token| Google
```

## Dependency rules

- Clients may depend on shared TypeScript packages; shared packages do not
  depend on a client.
- `@medical/shared` contains portable contracts and must not import browser or
  React Native APIs.
- `@medical/api-client` contains portable HTTP behavior. Platform session/token
  storage is injected by each client.
- React components are not currently shared across Next.js and React Native.
  M12 will review shared headless logic, tokens and component boundaries.
- Backend routes call backend services; clients never connect directly to the
  database.
- Ingestion code may populate PostgreSQL through controlled scripts but never
  mutates the immutable raw dataset.

## Authentication sequence

```mermaid
sequenceDiagram
    participant U as User
    participant C as Web/native client
    participant G as Google
    participant A as FastAPI
    participant D as PostgreSQL
    U->>C: Choose Sign in with Google
    C->>G: Platform-specific OAuth request
    G-->>C: Signed Google ID token
    C->>A: POST /api/auth/google {id_token}
    A->>G: Verify signature, issuer and audience
    A->>D: Find/create user and session
    A-->>C: Application access/refresh tokens and profile
```
