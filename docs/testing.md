# Test Plan

## Automated checks

Run each module independently:

```sh
cd protocol && go test ./... && go vet ./...
cd ../client && go test ./... && go vet ./...
cd ../server && go test ./... && go vet ./...
```

## Local integration test

1. Create a local CA and a server certificate with a DNS SAN (for example `localhost`).
2. Start the server with the certificate, private key and a high-entropy token.
3. Start the client with the CA certificate, matching TLS server name and the same token.
4. Configure curl or a browser to use SOCKS5 at `127.0.0.1:1080`.
5. Verify HTTPS access and inspect server logs.
6. Repeat with a wrong token and an untrusted CA; both connections must fail.

## Network fault matrix

| Condition | Expected behavior |
|---|---|
| TCP/TLS reachable | CONNECT succeeds |
| Server certificate untrusted | Client refuses connection |
| Wrong shared token | Server rejects tunnel |
| Bridge unavailable | Client reports connection failure |
| Destination refuses connection | SOCKS5 reports connection failure |
| UDP unavailable | No effect on current TCP/TLS baseline |
| Bridge endpoint blocked | No automatic alternate bridge until discovery/failover is implemented |
| Active connection interrupted | Current TCP stream fails; no transparent migration claim |
| Configuration signature invalid | Signed config verifier rejects it |

## Performance measurements

Record connect success rate, TLS handshake time, RTT, throughput, connection failure rate, CPU and memory. Test from independent networks and repeat measurements; one ISP or one test run is not representative.

Do not publish a claim of censorship resistance without a documented threat model and reproducible tests across relevant networks.
