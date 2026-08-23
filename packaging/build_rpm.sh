#!/usr/bin/env bash
# Gera o .rpm a partir do conteúdo do .deb (evita conflitos de conversão de dependências).
set -euo pipefail

DEB="$1"
VERSION="${2:-0.1.0}"
OUT_DIR="$(pwd)/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

dpkg-deb -x "$DEB" "$STAGE"

cd "$STAGE"
fpm -s dir -t rpm \
  --name powerzap \
  --version "$VERSION" \
  --iteration 1 \
  --license MIT \
  --architecture x86_64 \
  --description "Agendador de mensagens WhatsApp com Evolution API" \
  --url "https://github.com/HonoravelMacho/powerzap-" \
  --depends systemd \
  --depends gtk3 \
  --depends mpv-libs \
  --rpm-os linux \
  --package "$OUT_DIR/powerzap-${VERSION}.rpm" \
  .

echo "RPM gerado: $OUT_DIR/powerzap-${VERSION}.rpm"
