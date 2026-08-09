#!/usr/bin/env bash
# Mobile Release Archive Script (099/FR-008, Story 3)
#
# Produces an App Store Connect-ready .ipa from mobile/netclaw-mobile's
# Runner scheme, once a paid Apple Developer Program account is active.
#
# Usage: ./scripts/mobile-release-archive.sh
#
# Prerequisites:
#   - A paid Apple Developer Program membership, with the Runner target's
#     code signing moved to that team (see docs/MOBILE-RELEASE.md)
#   - mobile/netclaw-mobile/ExportOptions.plist's teamID filled in
#   - Xcode + command line tools installed

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOBILE_DIR="$REPO_ROOT/mobile/netclaw-mobile"
EXPORT_OPTIONS="$MOBILE_DIR/ExportOptions.plist"
ARCHIVE_PATH="$MOBILE_DIR/build/Runner.xcarchive"
EXPORT_PATH="$MOBILE_DIR/build/export"

cd "$MOBILE_DIR"

CURRENT_TEAM=$(grep -m1 'DEVELOPMENT_TEAM = ' ios/Runner.xcodeproj/project.pbxproj | sed -E 's/.*DEVELOPMENT_TEAM = ([A-Z0-9]+);/\1/')

# The free/Personal team ID this project shipped with (see research.md R5/R6
# and Runner.entitlements) -- if it's still set, code signing hasn't been
# moved to the paid team yet, and this archive would fail or (worse) silently
# produce a non-distributable build.
FREE_TEAM_ID="A49777FMJG"
if [ "$CURRENT_TEAM" = "$FREE_TEAM_ID" ]; then
  echo -e "${RED}error:${NC} DEVELOPMENT_TEAM is still the free/Personal team ($FREE_TEAM_ID)."
  echo "Move Runner's code signing to your paid Apple Developer Program team first"
  echo "(Xcode -> Runner target -> Signing & Capabilities -> Team), then re-run this script."
  echo "See docs/MOBILE-RELEASE.md."
  exit 1
fi

if grep -q "REPLACE_WITH_PAID_TEAM_ID" "$EXPORT_OPTIONS"; then
  echo -e "${RED}error:${NC} $EXPORT_OPTIONS still has the placeholder teamID."
  echo "Fill in your paid team ID (developer.apple.com/account -> Membership) and re-run."
  exit 1
fi

echo -e "${GREEN}==>${NC} Archiving Runner (team: $CURRENT_TEAM)..."
xcodebuild archive \
  -project ios/Runner.xcodeproj \
  -scheme Runner \
  -configuration Release \
  -archivePath "$ARCHIVE_PATH" \
  -destination "generic/platform=iOS"

echo -e "${GREEN}==>${NC} Exporting for App Store Connect..."
xcodebuild -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist "$EXPORT_OPTIONS"

echo -e "${GREEN}==>${NC} Done. Exported .ipa: $EXPORT_PATH"
echo -e "${YELLOW}Next:${NC} upload via Transporter or 'xcrun altool --upload-app', then complete"
echo "App Store Connect's listing (screenshots, privacy-policy URL) per docs/MOBILE-RELEASE.md."
