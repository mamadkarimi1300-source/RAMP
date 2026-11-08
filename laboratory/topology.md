# RAMP Laboratory Topology

## Logical topology

```text
Workload / curl
     |
     | SOCKS5
     v
RAMP Client (172.28.10.10)
     |
     | route via 172.28.10.2
     v
Network Emulator
     |
     | 172.28.20.2 -> 172.28.20.10
     v
RAMP Bridge (172.28.20.10)
     |
     | destination TCP
     v
Controlled Destination (172.28.20.11)

All roles ----> Laboratory collector ----> Run results / reports
```

## Network zones

The initial Docker topology uses two isolated subnets:

- **Client zone:** `172.28.10.0/24`; client at `172.28.10.10`, router at `172.28.10.2`.
- **Bridge zone:** `172.28.20.0/24`; router at `172.28.20.2`, bridge at `172.28.20.10`, destination at `172.28.20.11`.

The client has a route for `172.28.20.0/24` via `172.28.10.2`. The bridge has a return route for `172.28.10.0/24` via `172.28.20.2`. The Docker network gateway addresses are not assigned to the router. These subnets must be checked for conflicts with existing VPN, LAN and Docker networks.

The destination is reachable from the bridge-side network so destination traffic is not accidentally shaped as if it were part of the client-to-bridge link.

## Traffic path validation

Before accepting any measurement:

1. Confirm the client can reach the bridge only through the emulation router.
2. Capture packets on both router interfaces and confirm the request and return traffic traverse them.
3. Apply a non-zero delay and verify that observed tunnel RTT changes.
4. Remove the impairment and verify the baseline returns.
5. Confirm the bridge can reach the destination independently.
6. Confirm that destination-side traffic is not unintentionally traversing the client-to-bridge impairment.

A scenario is invalid if the traffic bypasses the emulator or if the impairment is applied to the wrong interface.

## Isolation and safety

- The SOCKS5 listener is published on host loopback only; it listens on the client container interface inside the isolated lab network.
- Use test-only tokens and locally generated certificates.
- Do not mount production secrets into containers.
- Keep the lab isolated from the host's default network and avoid exposing the bridge port publicly.
- Pin container image versions for reproducibility.
- Record the host OS, Docker version, kernel, CPU and memory with each experiment.

## Baseline comparison paths

1. **Direct baseline:** workload connects from the client container directly to the controlled destination; this still crosses the emulated transit router.
2. **RAMP fixed path:** workload uses the existing client-to-bridge TCP/TLS path and the same destination.
3. **RAMP adaptive:** enabled only after live measurement, selector integration and route behavior are implemented and verified.

Do not label the current selector primitives as adaptive operation until real measurements drive decisions in the request path.
