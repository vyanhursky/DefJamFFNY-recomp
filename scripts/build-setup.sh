#!/bin/bash
# Build the game-free macOS setup (Apple Silicon): Def Jam Setup.app inside a disk image.
# Never analyzes or builds a dump. Needs the Xcode Command Line Tools and Python 3.11+;
# pass --development for a local prototype from a dirty checkout (release workflows must not).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
DEVELOPMENT=()
[ "${1:-}" = "--development" ] && DEVELOPMENT=(--development)
VERSION=$(sed -n 's/^project(defjam_recomp VERSION \([0-9.]*\).*/\1/p' CMakeLists.txt)
OUT="$ROOT/build/setup-macos"
rm -rf "$OUT"
mkdir -p "$OUT"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
PYTHON="${PYTHON:-python3}"

# 1. The launcher app that setup copies next to the game.
LAUNCHER="$OUT/launcher/Def Jam Recompiled.app"
mkdir -p "$LAUNCHER/Contents/MacOS" "$LAUNCHER/Contents/Resources"
sed "s/@VERSION@/$VERSION/g" setup/macos/Launcher/Info.plist > "$LAUNCHER/Contents/Info.plist"
swiftc -O -target arm64-apple-macos11.0 setup/macos/Launcher/main.swift -o "$LAUNCHER/Contents/MacOS/DefJamLauncher"
codesign --force --sign - "$LAUNCHER"

# 2. The payload: source, Python, CMake, Ninja, the runtime libraries and that launcher.
"$PYTHON" scripts/package-setup.py --platform macos-arm64 --launcher "$LAUNCHER" \
    --output "$OUT/setup-payload.zip" "${DEVELOPMENT[@]+"${DEVELOPMENT[@]}"}"

# 3. The wizard app, carrying the payload and its digest.
APP="$OUT/image/Def Jam Setup.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
SHA=$(shasum -a 256 "$OUT/setup-payload.zip" | cut -d' ' -f1)
echo "let payloadSHA256 = \"$SHA\"" > "$OUT/PayloadDigest.swift"
swiftc -O -target arm64-apple-macos11.0 setup/macos/Setup/main.swift "$OUT/PayloadDigest.swift" \
    -o "$APP/Contents/MacOS/DefJamSetup"
cp "$OUT/setup-payload.zip" "$APP/Contents/Resources/payload.zip"
sed "s/@VERSION@/$VERSION/g" setup/macos/Setup/Info.plist > "$APP/Contents/Info.plist"
codesign --force --sign - "$APP"

# 4. The disk image: the app, the first-run notes and the third-party licenses.
cp setup/macos/README-FIRST.txt "$OUT/image/READ ME FIRST.txt"
mkdir "$OUT/image/Licenses"
unzip -q -o "$OUT/setup-payload.zip" 'licenses/*' -d "$OUT/licenses-unpacked"
cp "$OUT"/licenses-unpacked/licenses/* "$OUT/image/Licenses/"
cp LICENSE "$OUT/image/Licenses/Def-Jam-Recompiled-MIT.txt"
hdiutil create -volname "Def Jam Recompiled Setup" -srcfolder "$OUT/image" -ov -format UDZO "$OUT/DefJamSetup.dmg" > /dev/null

# 5. Inventory, checksum and provenance of exactly what a release would attach.
"$PYTHON" scripts/check-setup-assets.py --payload "$OUT/setup-payload.zip" --installer "$OUT/DefJamSetup.dmg" \
    --output-dir "$OUT/setup-assets" "${DEVELOPMENT[@]+"${DEVELOPMENT[@]}"}"
echo "Built $OUT/setup-assets"
