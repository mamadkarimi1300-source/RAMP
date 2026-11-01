# Threat Model and Security Boundaries

## Protected assets

- Shared access token and TLS private key.
- Integrity and authenticity of bridge configuration.
- Application payload confidentiality in transit between client and bridge.
- Availability of client and bridge processes.
- User privacy and minimal operational telemetry.

## Baseline protections

- TLS 1.3 with certificate-chain and server-name validation on the client.
- Shared-token authentication inside the encrypted TLS channel.
- Constant-time token comparison after equal-length validation.
- Versioned and length-bounded handshake fields.
- Ed25519 signature verification for configuration payloads.
- Loopback-only SOCKS5 listener by default.

## Risks not solved by this baseline

- A shared static token can be copied or leaked; there is no per-user identity, revocation service or token rotation protocol yet.
- TLS alone does not guarantee resistance to traffic classification, active probing, SNI interference or protocol blocking.
- No traffic-shaping or pluggable-transport implementation is included.
- The current server is a single bridge and can be blocked or overloaded.
- No rate limiter, abuse detection, per-user quota or administrative control plane is implemented.
- No UDP forwarding or DNS-over-HTTPS subsystem is included.
- Telemetry collection and privacy-preserving aggregation are not implemented.

## Deployment rules

1. Never commit private keys, certificates containing private material, tokens or production configuration.
2. Keep the client SOCKS5 listener bound to loopback unless a separate authenticated local-access design is added.
3. Restrict the bridge port with firewall policy and operational rate limits.
4. Use unique, high-entropy tokens and distribute them through a secure channel.
5. Rotate TLS certificates and shared tokens; plan revocation before inviting multiple users.
6. Do not log destination payloads or browsing history.
7. Treat bridge lists and remote configuration as untrusted until signature verification succeeds.

## Limitations

RAMP cannot restore connectivity during a complete loss of international routing or physical connectivity. It is an experimental architecture for evaluating alternative access paths under selective filtering and network disruption; no guarantee of bypass success is made.
