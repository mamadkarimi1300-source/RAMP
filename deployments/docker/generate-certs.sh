#!/bin/sh
set -eu

OUT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/certs"
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

if [ -e "$OUT_DIR/ca.key" ] || [ -e "$OUT_DIR/server.key" ]; then
  echo "certificate files already exist in $OUT_DIR; remove them explicitly to regenerate" >&2
  exit 1
fi

openssl req -x509 -newkey rsa:3072 -nodes \
  -keyout "$OUT_DIR/ca.key" \
  -out "$OUT_DIR/ca.crt" \
  -days 365 \
  -subj "/CN=RAMP Laboratory Local CA"

openssl req -newkey rsa:2048 -nodes \
  -keyout "$OUT_DIR/server.key" \
  -out "$OUT_DIR/server.csr" \
  -subj "/CN=ramp-bridge"

cat > "$OUT_DIR/server.ext" <<'EOF'
subjectAltName=DNS:ramp-bridge
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF

openssl x509 -req \
  -in "$OUT_DIR/server.csr" \
  -CA "$OUT_DIR/ca.crt" \
  -CAkey "$OUT_DIR/ca.key" \
  -CAcreateserial \
  -out "$OUT_DIR/server.crt" \
  -days 365 \
  -sha256 \
  -extfile "$OUT_DIR/server.ext"

rm -f "$OUT_DIR/server.csr" "$OUT_DIR/server.ext" "$OUT_DIR/ca.srl"
chmod 600 "$OUT_DIR/ca.key" "$OUT_DIR/server.key"
chmod 644 "$OUT_DIR/ca.crt" "$OUT_DIR/server.crt"
echo "Local lab certificates created in $OUT_DIR"
