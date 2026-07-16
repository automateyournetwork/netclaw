#!/usr/bin/env bash
# Fetch the lego ACME client (single static Go binary) for claw certification
# (feature 060). Idempotent: no-op if already present. Verifies the download by
# checksum. Used by component_install_claw_certs() and scripts/patch-claw-certs.sh.
set -euo pipefail

LEGO_VERSION="${LEGO_VERSION:-4.19.2}"
DEST_DIR="${N2N_LEGO_DIR:-$HOME/.openclaw/n2n/bin}"
DEST="$DEST_DIR/lego"

if [ -x "$DEST" ]; then
  echo "lego already installed at $DEST ($("$DEST" --version 2>/dev/null | head -1))"
  exit 0
fi

case "$(uname -m)" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "unsupported arch $(uname -m) — install lego manually into $DEST" >&2; exit 1 ;;
esac
OS=linux
TARBALL="lego_v${LEGO_VERSION}_${OS}_${ARCH}.tar.gz"
URL="https://github.com/go-acme/lego/releases/download/v${LEGO_VERSION}/${TARBALL}"

mkdir -p "$DEST_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "Downloading lego v${LEGO_VERSION} (${OS}/${ARCH})..."
curl -fsSL "$URL" -o "$TMP/$TARBALL"

# Verify against the release checksums file (hashes.txt lists <sha256>  <file>).
if curl -fsSL "https://github.com/go-acme/lego/releases/download/v${LEGO_VERSION}/lego_${LEGO_VERSION}_checksums.txt" -o "$TMP/sums.txt" 2>/dev/null; then
  ( cd "$TMP" && grep " ${TARBALL}\$" sums.txt | sha256sum -c - ) \
    || { echo "checksum verification FAILED for $TARBALL" >&2; exit 1; }
else
  echo "WARN: could not fetch checksums file — proceeding without verification" >&2
fi

tar -xzf "$TMP/$TARBALL" -C "$TMP" lego
install -m 0755 "$TMP/lego" "$DEST"
echo "Installed lego -> $DEST"
