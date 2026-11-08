# Docker Laboratory Deployment

This directory contains the first local Docker testbed implementation. It builds the existing RAMP client and bridge as separate images and places a Linux traffic-emulation router between isolated client and bridge network zones.

## Topology

- `ramp-client`: built from the existing `client` Go module.
- `ramp-bridge`: built from the existing `server` Go module.
- `destination`: controlled Python HTTP workload endpoint at `172.28.20.11:8080` on the bridge-side network.
- `netem-router`: dual-homed Linux router at `172.28.10.2` and `172.28.20.2`; it is the intended transit path between client and bridge.
- Client and bridge each have a separate persistent SQLite volume.

The client has a specific route to the bridge-side subnet through the router. The bridge and the controlled destination each have a return route to the client-side subnet through the same router. The destination return route is essential: without it, direct-baseline replies could bypass the emulator and invalidate the comparison. The client container includes curl so direct and proxied requests can originate from the same workload environment.

## Prerequisites

- Docker Desktop with the WSL2 backend and Docker Compose v2.
- A WSL2 Linux shell with OpenSSL and curl.
- Go is not required on the host for container builds.
- The subnets `172.28.10.0/24` and `172.28.20.0/24` must not conflict with existing VPN, LAN or Docker networks.

## Automated build and smoke test

From the repository root in WSL2, run:

```sh
sh laboratory/scripts/docker-smoke-test.sh
```

The script generates local-only certificates when needed, validates the Compose model, builds and starts all services, compares direct and SOCKS5 responses from the same client, captures client-to-bridge and destination-to-client packets on the transit router, and verifies that a configured NetEm delay is installed. It prints service logs on failure and removes the containers afterward.

To leave the containers running after a successful test for interactive inspection:

```sh
RAMP_LAB_KEEP_RUNNING=1 sh laboratory/scripts/docker-smoke-test.sh
```

The same smoke test runs automatically in the `.github/workflows/docker-lab.yml` workflow on pushes and pull requests targeting `master`. A passing workflow validates the GitHub-hosted Linux Docker environment; it does not replace a separate validation on the developer's Docker Desktop/WSL2 host.

## Start the lab

From the repository root in WSL2:

1. Generate local-only TLS credentials:

   ```sh
   sh deployments/docker/generate-certs.sh
   ```

2. Set a unique lab token in the current shell:

   ```sh
   export RAMP_TOKEN="$(openssl rand -hex 32)"
   ```

3. Start the testbed:

   ```sh
   docker compose -f deployments/docker/compose.yaml up --build -d
   ```

4. Inspect service status and logs:

   ```sh
   docker compose -f deployments/docker/compose.yaml ps
   docker compose -f deployments/docker/compose.yaml logs -f netem-router ramp-bridge ramp-client
   ```

5. Compare a direct request with a request through RAMP from the same client container:

   ```sh
   # Direct client-to-destination baseline (still crosses the emulated transit router).
   docker compose -f deployments/docker/compose.yaml exec ramp-client curl --fail --show-error http://172.28.20.11:8080/health

   # Same destination through the local RAMP SOCKS5 ingress.
   docker compose -f deployments/docker/compose.yaml exec ramp-client curl --fail --show-error --socks5-hostname 127.0.0.1:1080 http://lab-destination:8080/health
   ```

   You can also test from the host using `curl --socks5-hostname 127.0.0.1:1080 http://lab-destination:8080/health`.

## Run repeatable experiments

The destination exposes `/health` and `/payload?bytes=N` (1 byte to 100 MiB). The experiment runner uses only Python's standard library and writes a manifest, timestamped raw JSONL samples, qdisc/container snapshots, summary statistics and a Markdown report.

From the repository root:

```sh
python laboratory/scripts/run_experiments.py --scenario baseline --scenario latency-100ms --repetitions 3 --warmup 1 --payload-bytes 10485760
```

Run all profiles from `laboratory/scenarios/matrix.json` by omitting `--scenario`. Use `--mode direct` or `--mode ramp-fixed` for a single path, or the default `--mode both` for a direct-versus-RAMP comparison. Results are written under `laboratory/results/<date>/<experiment-id>/` and are ignored by Git.

The report includes bridge RTT (ICMP), packet-loss observations, verified TLS handshake duration, goodput, transfer duration, success rate, mean, median, standard deviation, p95 and relative goodput/transfer-duration changes for RAMP versus the direct baseline. The TLS probe measures the TLS handshake only, not the RAMP OPEN application exchange. Curl's connect time in RAMP mode measures the local SOCKS5 peer, not the internal TLS handshake; it must not be reported as TLS handshake duration. CPU/memory snapshots and `tc -s qdisc` output are retained as raw supporting observations.

## Apply a network condition

Recreate the router with the selected environment variables. Example for 100 ms delay in each direction and 1% packet loss:

```sh
RAMP_TOKEN="$RAMP_TOKEN" RAMP_NETEM_DELAY=100ms RAMP_NETEM_LOSS=1% docker compose -f deployments/docker/compose.yaml up -d --force-recreate netem-router
```

For a 5 Mbit/s rate limit:

```sh
RAMP_TOKEN="$RAMP_TOKEN" RAMP_NETEM_RATE=5mbit docker compose -f deployments/docker/compose.yaml up -d --force-recreate netem-router
```

The delay is applied on both router egress interfaces, so 100 ms configured in this way is approximately 100 ms added per direction (before other network effects). Confirm the actual effect with independent measurements; do not assume the configured value equals measured end-to-end RTT.

## Prove the traffic path

Inspect the router's interface addresses:

```sh
docker compose -f deployments/docker/compose.yaml exec netem-router ip -o -4 addr show
```

Identify which interface owns `172.28.10.2` and which owns `172.28.20.2`, then capture on both:

```sh
docker compose -f deployments/docker/compose.yaml exec netem-router tcpdump -ni eth0
docker compose -f deployments/docker/compose.yaml exec netem-router tcpdump -ni eth1
```

Replace `eth0` and `eth1` with the interface names shown by the first command. A valid run must show the client-to-bridge packets crossing the router in both directions.

## Stop and clean up

```sh
docker compose -f deployments/docker/compose.yaml down
```

To remove lab databases as well:

```sh
docker compose -f deployments/docker/compose.yaml down -v
```

The second command permanently deletes the named client and server database volumes.

## Important validation status

The Docker lab has passed its GitHub Actions integration run on a GitHub-hosted Ubuntu runner: all images built, direct and SOCKS5 requests succeeded, client-to-bridge and destination-return packets were captured on the transit router, and the 50 ms NetEm qdisc was installed. This does not yet validate the user's local Docker Desktop/WSL2 environment or independently prove the measured RTT effect. Before accepting research benchmark data, verify:

- Both forward and return traffic cross the emulator (capture on both router interfaces).
- A non-zero impairment changes measured client-to-bridge RTT.
- The direct path cannot bypass the emulator.
- Direct and SOCKS5 requests to the same destination both succeed.
- Removing impairment restores the baseline.

Do not treat this initial Compose scaffold as a validated benchmark environment until those checks pass.
