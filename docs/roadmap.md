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
- [x] Add a controlled HTTP destination with configurable deterministic payloads and direct-versus-SOCKS5 smoke tests.
- [x] Add a machine-readable scenario matrix and standard-library experiment runner with repetitions, warm-ups and raw JSONL samples.
- [x] Add initial goodput/transfer timing, qdisc counters, container CPU/memory snapshots and statistical Markdown/JSON reports.
- [x] Add Python unit tests and CI workflow integration for the laboratory runner.
- [x] Build all images and validate Compose configuration in GitHub Actions on Ubuntu.
- [x] Capture client-to-bridge and destination-to-client packets on the transit router in CI.
- [x] Smoke-test direct and SOCKS5 paths and verify NetEm qdisc installation.
- [ ] Repeat validation on local Docker Desktop / WSL2.
- [ ] Verify each impairment profile's effect using independent RTT measurements.
- [x] Add client-to-bridge ICMP RTT/packet-loss probes and a certificate-verified bridge TLS handshake probe.
- [ ] Add active-session counts and recovery-duration instrumentation.
- [ ] Add statistical direct-baseline deltas and confidence intervals to the report.
- [ ] Validate all impairment profiles against independent measurements and prove no route bypass.
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
