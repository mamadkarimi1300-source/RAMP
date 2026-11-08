# Roadmap

## Baseline currently in repository

- [x] Separate client, server and protocol Go modules.
- [x] TLS 1.3 client-to-bridge tunnel with certificate verification.
- [x] Shared-token validation inside TLS.
- [x] SOCKS5 CONNECT ingress.
- [x] TCP destination connector on the server.
- [x] Versioned, bounded wire handshake.
- [x] Session lifecycle manager and tests.
- [x] Candidate scoring primitive and tests.
- [x] Bounded retry backoff and tests.
- [x] Ed25519 signed-configuration verification and tests.
- [x] Server component health registry.
- [x] CI test/vet workflow.
- [x] Laboratory topology and separation-of-concerns specification.
- [x] Initial network scenario matrix and experiment metadata/metric contract.

## Laboratory implementation stages

- [ ] Build and validate multi-stage Docker images for client and server without merging Go module boundaries.
- [ ] Implement isolated client-side and bridge-side Docker networks with a transit emulator as the only client-to-bridge route.
- [ ] Provision lab-only CA/certificate and token without committing secrets.
- [ ] Add controlled HTTP/TCP destination and repeatable workload generator.
- [ ] Apply and verify bidirectional delay, jitter, packet loss and bandwidth profiles on the real transit path.
- [ ] Collect raw RTT, throughput/goodput, connect/handshake timing, CPU, memory and container/network counters.
- [ ] Add experiment runner, manifests, repetitions and machine-readable result output.
- [ ] Add report generation and baseline comparison.
- [ ] Add failure-injection tests for bridge unavailability and recovery behavior.

## v0.2 target

- [ ] QUIC transport adapter with integration tests.
- [ ] Multiple bridge configuration and discovery.
- [ ] Live RTT, throughput and failure measurement.
- [ ] Selector fed by live measurements, with hysteresis and retry budgets.
- [ ] Bridge health probes and bridge failover for new sessions.
- [ ] Structured logs with transport, bridge, outcome and recovery reason.
- [ ] Deployment manifests and reproducible local test environment.
- [ ] Multi-network test matrix and benchmark report.

## Selected v0.3 capabilities brought forward

- [x] Session state model.
- [x] Recovery state and bounded backoff primitive.
- [x] Signed configuration verification primitive.
- [x] Health registry.
- [ ] Key rotation and token revocation workflow.
- [ ] Durable transfer-resume protocol for explicitly resumable application transfers.
- [ ] Minimal privacy-preserving telemetry pipeline.
- [ ] Control-plane API and signed configuration distribution.

## Later work

- WebRTC / vetted pluggable transport adapters.
- Volunteer bridge enrollment and trust model.
- Distributed control-plane deployment.
- User interface and administrative dashboard.
- Scale, abuse-resistance and independent security review.

A checkbox is marked complete only when code and tests are present. A design placeholder or interface alone is not a completed transport or recovery feature. Laboratory design documents do not mean that the Docker testbed or its measurements are already operational.
