#!/usr/bin/env bash
# Converte o binário Linux empacotado (.deb) em .rpm usando fpm.
set -euo pipefail
DEB="$1"
VERSION="${2:-0.1.0}"
OUT_DIR="$(pwd)/dist"
fpm -s deb -t rpm \
  --name powerzap \
  --version "$VERSION" \
  --license MIT \
  --description "Agendador de mensagens WhatsApp com Evolution API" \
  --depends systemd \
  --rpm-os linux \
  --package "$OUT_DIR/powerzap-${VERSION}.rpm" \
  "$DEB"
echo "RPM gerado: $OUT_DIR/powerzap-${VERSION}.rpm"
