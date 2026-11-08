#!/bin/sh
set -eu

CLIENT_ADDR="172.28.10.2/"
BRIDGE_ADDR="172.28.20.2/"

CLIENT_IF="$(ip -o -4 addr show | awk -v addr="$CLIENT_ADDR" '$4 ~ ("^" addr) {print $2; exit}')"
BRIDGE_IF="$(ip -o -4 addr show | awk -v addr="$BRIDGE_ADDR" '$4 ~ ("^" addr) {print $2; exit}')"

if [ -z "$CLIENT_IF" ] || [ -z "$BRIDGE_IF" ]; then
  echo "could not identify client-zone and bridge-zone interfaces" >&2
  ip -o -4 addr show >&2
  exit 1
fi

sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -P FORWARD ACCEPT

DELAY="${RAMP_NETEM_DELAY:-0ms}"
JITTER="${RAMP_NETEM_JITTER:-0ms}"
LOSS="${RAMP_NETEM_LOSS:-0%}"
RATE="${RAMP_NETEM_RATE:-}"

apply_netem() {
  iface="$1"
  set -- tc qdisc replace dev "$iface" root netem

  if [ "$DELAY" != "0ms" ] || [ "$JITTER" != "0ms" ]; then
    set -- "$@" delay "$DELAY"
    if [ "$JITTER" != "0ms" ]; then set -- "$@" "$JITTER"; fi
  fi
  if [ "$LOSS" != "0%" ]; then set -- "$@" loss "$LOSS"; fi
  if [ -n "$RATE" ]; then set -- "$@" rate "$RATE"; fi

  if [ "$#" -gt 7 ]; then
    "$@"
  else
    tc qdisc del dev "$iface" root 2>/dev/null || true
  fi
}

# Egress shaping on both router interfaces applies impairment in both
# directions of the client<->bridge path. Destination traffic stays bridge-side.
apply_netem "$CLIENT_IF"
apply_netem "$BRIDGE_IF"

echo "RAMP lab router ready: client_if=$CLIENT_IF bridge_if=$BRIDGE_IF delay=$DELAY jitter=$JITTER loss=$LOSS rate=${RATE:-unlimited}"
exec tail -f /dev/null
