# RAMP Event Storage

## Deployment boundary

The shared `storage` Go module contains the event contract, asynchronous logger and SQLite repository. It is a library linked into the client and server processes; it is not a database server or remote storage API.

Each deployment writes to its own database:

- Client process: `data/client.db`.
- Bridge process: `data/server.db`.

Use `RAMP_CLIENT_DB_PATH` / `RAMP_SERVER_DB_PATH` or the corresponding `-db` flag to select another path. Database files, WAL files and shared-memory files are ignored by Git.

## Event schema

The `connection_logs` table stores:

| Column | Meaning |
|---|---|
| `id` | Local auto-increment row ID |
| `session_id` | Process-local connection/session identifier |
| `timestamp` | UTC event timestamp |
| `event_type` | Lifecycle or failure event |
| `destination` | Requested host and port, when known |
| `transport` | Current path label (currently `tls-tcp`) |
| `network` | Underlying network (currently `tcp`) |
| `latency_ms` | Connection timing measurement |
| `bytes_sent` | Bytes in the component's outbound direction |
| `bytes_received` | Bytes in the component's inbound direction |
| `status` | Result or lifecycle state |
| `error_message` | Failure detail, when available |

Indexes are created for timestamp, session ID, destination and event type. Schema creation is idempotent and runs when the database is opened.

## Event flow

The client records local SOCKS5 acceptance/handshake, transport selection, tunnel establishment/failure and final traffic counters. The server independently records incoming tunnel sessions, TLS/protocol failures, token rejection, egress connection outcomes and final traffic counters.

The two databases intentionally use separate process-local session IDs. Do not join them by session ID; correlating client and server records across deployments will require a future shared correlation ID in the RAMP wire protocol.

## Write behavior and limitations

Network handlers submit events to a bounded asynchronous queue (default capacity 1024). Database writes happen outside the request path. When the queue is full, events are dropped rather than blocking traffic; dropped events are counted. Database write failures are also counted and both counters are logged at process shutdown.

The current schema is an operational event log, not a metrics warehouse. It does not yet calculate throughput, rolling network quality, path scores, retention/rotation or dashboard queries. Latency currently represents the client-side time to open the tunnel or the server-side egress dial time; it is not a full end-to-end RTT measurement.
