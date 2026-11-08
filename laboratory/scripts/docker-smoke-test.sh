#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="deployments/docker/compose.yaml"
CERT_DIR="deployments/docker/certs"
LOG_FILE="$(mktemp)"
CAPTURE_PID=""

export RAMP_TOKEN="${RAMP_TOKEN:-$(openssl rand -hex 32)}"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

cleanup() {
  status=$?
  if [ -n "$CAPTURE_PID" ]; then
    kill "$CAPTURE_PID" 2>/dev/null || true
    wait "$CAPTURE_PID" 2>/dev/null || true
  fi
  if [ "$status" -ne 0 ]; then
    echo "Docker laboratory failed; service logs follow:" >&2
    compose logs --no-color >&2 || true
  fi
  if [ "${RAMP_LAB_KEEP_RUNNING:-0}" != "1" ]; then
    compose down --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -f "$LOG_FILE"
  exit "$status"
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
docker compose version >/dev/null
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }

if [ ! -s "$CERT_DIR/ca.crt" ] || [ ! -s "$CERT_DIR/server.key" ]; then
  sh deployments/docker/generate-certs.sh
fi

echo "[1/6] Validate Compose configuration"
compose config --quiet

echo "[2/6] Build and start the complete laboratory"
compose up --build -d

echo "[3/6] Wait for the destination and RAMP SOCKS5 path"
ready=0
i=0
while [ "$i" -lt 45 ]; do
  if compose exec -T ramp-client curl --fail --silent --show-error --max-time 3 http://172.28.20.11/ >/dev/null 2>&1; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "Destination is not reachable from the client through the configured route" >&2
  exit 1
fi

direct="$(compose exec -T ramp-client curl --fail --silent --show-error --max-time 10 http://172.28.20.11/)"
if [ -z "$direct" ]; then
  echo "Direct baseline returned an empty response" >&2
  exit 1
fi

proxied_ready=0
i=0
while [ "$i" -lt 30 ]; do
  if proxied="$(compose exec -T ramp-client curl --fail --silent --show-error --max-time 5 --socks5-hostname 127.0.0.1:1080 http://lab-destination/ 2>/dev/null)"; then
    proxied_ready=1
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$proxied_ready" -ne 1 ] || [ -z "$proxied" ]; then
  echo "RAMP SOCKS5 request to the controlled destination failed" >&2
  exit 1
fi
if [ "$direct" != "$proxied" ]; then
  echo "Direct and RAMP requests returned different destination content" >&2
  exit 1
fi
echo "Direct baseline: PASS"
echo "RAMP SOCKS5/TLS path: PASS"

echo "[4/6] Verify client-to-bridge packets cross the transit router"
compose exec -T netem-router sh -c "timeout 15 tcpdump -ni any -c 1 'src host 172.28.10.10 and dst host 172.28.20.10'" >"$LOG_FILE" 2>&1 &
CAPTURE_PID=$!
sleep 1
compose exec -T ramp-client curl --fail --silent --show-error --max-time 10 --socks5-hostname 127.0.0.1:1080 http://lab-destination/ >/dev/null
if ! wait "$CAPTURE_PID"; then
  CAPTURE_PID=""
  cat "$LOG_FILE" >&2
  echo "No client-to-bridge packet was observed on the transit router" >&2
  exit 1
fi
CAPTURE_PID=""
if ! grep -q "172.28.10.10" "$LOG_FILE" || ! grep -q "172.28.20.10" "$LOG_FILE"; then
  cat "$LOG_FILE" >&2
  echo "Transit-router capture did not contain the expected client and bridge addresses" >&2
  exit 1
fi
echo "Transit packet capture: PASS"

echo "[5/6] Apply a controlled delay and verify the qdisc"
RAMP_NETEM_DELAY=50ms docker compose -f "$COMPOSE_FILE" up -d --force-recreate netem-router
sleep 2
if ! compose exec -T netem-router tc qdisc show | grep -q "netem.*delay 50ms"; then
  compose exec -T netem-router tc qdisc show >&2 || true
  echo "The configured 50ms NetEm delay was not installed" >&2
  exit 1
fi
echo "NetEm delay installation: PASS"

echo "[6/6] Laboratory smoke test completed"
echo "All Docker laboratory checks passed."
if [ "${RAMP_LAB_KEEP_RUNNING:-0}" = "1" ]; then
  echo "RAMP_LAB_KEEP_RUNNING=1: containers and database volumes were left running."
fi
