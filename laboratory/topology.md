# RAMP Laboratory Topology

## Logical topology

```text
Workload / curl
     |
     | SOCKS5
     v
RAMP Client
     |
     | TCP + TLS 1.3 + RAMP protocol
     v
Network Emulator
     |
     | shaped / impaired link
     v
RAMP Bridge
     |
     | destination TCP connection
     v
Controlled Destination

All roles ----> Laboratory collector ----> Run results / reports
```

## Network zones

The intended local testbed uses separate network zones:

- **Client zone:** application workload and RAMP client.
- **Bridge zone:** RAMP bridge and controlled destination.
- **Transit zone:** network-emulation router connecting the client and bridge zones.

The client must not have a direct route to the bridge that bypasses the emulator. The bridge must have a return route through the emulator for the client-side tunnel. The destination is reachable from the bridge-side network so destination traffic is not accidentally shaped as if it were part of the client-to-bridge link.

The exact Docker network names, CIDRs, static addresses and interface discovery rules belong in the deployment configuration. They must be documented and checked for conflicts before startup.

## Traffic path validation

Before accepting any measurement:

1. Confirm the client can reach the bridge only through the emulation router.
2. Capture or inspect traffic on both sides of the router.
3. Apply a non-zero delay and verify that observed tunnel RTT changes.
4. Remove the impairment and verify the baseline returns.
5. Confirm the bridge can reach the destination independently.
6. Confirm that destination-side traffic is not unintentionally traversing the client-to-bridge impairment.

A scenario is invalid if the traffic bypasses the emulator or if the impairment is applied to the wrong interface.

## Isolation and safety

- Bind the SOCKS5 listener to loopback unless a separately reviewed lab-only network policy is in place.
- Use test-only tokens and locally generated certificates.
- Do not mount production secrets into containers.
- Keep the lab isolated from the host's default network and avoid exposing the bridge port publicly.
- Pin container image versions for reproducibility.
- Record the host OS, Docker version, kernel, CPU and memory with each experiment.

## Baseline comparison paths

1. **Direct baseline:** workload connects directly to the controlled destination.
2. **RAMP fixed path:** workload uses the existing client-to-bridge TCP/TLS path.
3. **RAMP adaptive:** enabled only after live measurement, selector integration and route behavior are implemented and verified.

Do not label the current selector primitives as adaptive operation until real measurements drive decisions in the request path.
