# Docker Laboratory Deployment

This directory contains the first local Docker testbed implementation. It builds the existing RAMP client and bridge as separate images and places a Linux traffic-emulation router between isolated client and bridge network zones.

## Topology

- `ramp-client`: built from the existing `client` Go module.
- `ramp-bridge`: built from the existing `server` Go module.
- `destination`: controlled Nginx HTTP endpoint on the bridge-side network.
- `netem-router`: dual-homed Linux router; it is the intended transit path between client and bridge.
- Client and bridge each have a separate persistent SQLite volume.

The client has a specific route to the bridge-side subnet through the router. The bridge has a return route to the client-side subnet through the same router. The destination is reachable from the bridge-side network.

## Prerequisites

- Docker Desktop with the WSL2 backend and Docker Compose v2.
- A WSL2 Linux shell with OpenSSL and curl.
- Go is not required on the host for container builds.
- The subnets `172.28.10.0/24` and `172.28.20.0/24` must not conflict with existing VPN, LAN or Docker networks.

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

5. Send an HTTP request through the local SOCKS5 listener:

   ```sh
   curl --fail --show-error --socks5-hostname 127.0.0.1:1080 http://lab-destination/
   ```

The hostname is resolved from the bridge-side network. The local SOCKS5 port is published only on host loopback.

## Apply a network condition

Recreate the router with the selected environment variables. Example for 100 ms delay in each direction and 1% packet loss:

```sh
RAMP_TOKEN="$RAMP_TOKEN" RAMP_NETEM_DELAY=100ms RAMP_NETEM_LOSS=1% docker compose -f deployments/docker/compose.yaml up --build -d --force-recreate netem-router
```

For a 5 Mbit/s rate limit:

```sh
RAMP_TOKEN="$RAMP_TOKEN" RAMP_NETEM_RATE=5mbit docker compose -f deployments/docker/compose.yaml up -d --force-recreate netem-router
```

The delay is applied on both router egress interfaces, so 100 ms configured in this way is approximately 100 ms added per direction (before other network effects). Confirm the actual effect with independent measurements; do not assume the configured value equals measured end-to-end RTT.

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

The Compose topology and container build files are committed, but they have not yet been executed in this environment. Docker Desktop routing/forwarding rules may require adjustment. Before collecting benchmark data, verify:

- Both forward and return traffic cross the emulator (capture on both router interfaces).
- A non-zero impairment changes measured client-to-bridge RTT.
- The direct path cannot bypass the emulator.
- Client-to-destination requests succeed with the generated CA and lab token.
- Removing impairment restores the baseline.

Do not treat this initial Compose scaffold as a validated benchmark environment until those checks pass.
