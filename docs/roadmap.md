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

## Laboratory scaffold committed (runtime validation pending)

- [x] Add separate Docker build definitions for the existing client and server modules.
- [x] Add Compose topology with client zone, bridge zone and a transit-router service.
- [x] Add local-only CA and bridge certificate generation helper.
- [x] Add Linux traffic-shaping configuration for delay, jitter, loss and rate limits.
- [x] Add a controlled HTTP destination and direct-versus-SOCKS5 smoke-test instructions.
- [ ] Build both images and validate Compose configuration on Docker Desktop / WSL2.
- [ ] Prove forward and return traffic traverse the emulator; confirm no bypass route exists.
- [ ] Verify each impairment profile against independent measurements.
- [ ] Add a repeatable workload runner with experiment IDs, repetitions and raw result manifests.
- [ ] Collect RTT, throughput/goodput, connect/handshake timing, CPU, memory and container/network counters.
- [ ] Add report generation and statistical baseline comparison.
- [ ] Add failure-injection tests for bridge unavailability and recovery behavior.

## v0.2 target

- [ ] QUIC transport adapter with integration tests.
- [ ] Multiple bridge configuration and discovery.
- [ ] Live RTT, throughput and failure measurement.
- [ ] Selector fed by live measurements, with hysteresis and retry budgets.
- [ ] Bridge health probes and bridge failover for new sessions.
- [ ] Structured logs with transport, bridge, outcome and recovery reason.
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

A checkbox is marked complete only when the corresponding files or code are present. Runtime-validation items remain unchecked until executed and verified. A design placeholder or interface alone is not a completed transport or recovery feature.
