#!/usr/bin/env bash
# Monta o pacote .deb a partir dos binários gerados pelo PyInstaller.
set -euo pipefail

VERSION="${1:-0.1.0}"
ARCH="$(dpkg --print-architecture)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/dist/debroot/powerzap_${VERSION}_${ARCH}"

rm -rf "$ROOT/dist/debroot"
mkdir -p \
  "$STAGE/DEBIAN" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/256x256/apps" \
  "$STAGE/usr/lib/systemd/user"

install -m 755 "$ROOT/dist/powerzap/powerzap" "$STAGE/usr/bin/powerzap"
install -m 755 "$ROOT/dist/powerzap-scheduler/powerzap-scheduler" "$STAGE/usr/bin/powerzap-scheduler"
install -m 644 "$ROOT/packaging/powerzap.desktop" "$STAGE/usr/share/applications/"
install -m 644 "$ROOT/assets/icon.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/powerzap.png"
install -m 644 "$ROOT/packaging/powerzap-scheduler.service" "$STAGE/usr/lib/systemd/user/"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: powerzap
Version: ${VERSION}
Section: net
Priority: optional
Architecture: ${ARCH}
Depends: libgl1, libglib2.0-0, systemd
Installed-Size: $(du -sk "$ROOT/dist/powerzap" | cut -f1)
Maintainer: HonoravelMacho <honoravelmacho@users.noreply.github.com>
Description: Agendador de mensagens WhatsApp com Evolution API
 PowerZap permite agendar e enviar mensagens do WhatsApp via
 Evolution API local, com calendário interativo, etiquetas
 coloridas e serviço de envio em background.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || true
for user_home in /home/*; do
  user="$(basename "$user_home")"
  if id "$user" >/dev/null 2>&1; then
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u $user)" \
      systemctl --user enable powerzap-scheduler.service >/dev/null 2>&1 || true
  fi
done
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/bash
set -e
for user_home in /home/*; do
  user="$(basename "$user_home")"
  if id "$user" >/dev/null 2>&1; then
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u $user)" \
      systemctl --user stop powerzap-scheduler.service >/dev/null 2>&1 || true
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u $user)" \
      systemctl --user disable powerzap-scheduler.service >/dev/null 2>&1 || true
  fi
done
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/prerm"

dpkg-deb --build --root-owner-group "$STAGE" "$ROOT/dist/powerzap_${VERSION}_${ARCH}.deb"
echo "Pacote gerado: dist/powerzap_${VERSION}_${ARCH}.deb"
