#!/bin/sh
# Fetches livesync-bridge at the pinned commit and installs its locked
# dependencies onto the state volume, once per commit, so a restart needs no
# internet. livesync-bridge publishes no image or release, hence this.
set -eu
APP="/state/app/$BRIDGE_COMMIT"
if [ -f "$APP/.installed" ]; then
  echo "livesync-bridge $BRIDGE_COMMIT already installed"
  exit 0
fi
rm -rf /state/app
mkdir -p "$APP"
deno eval "
const r = await fetch('https://codeload.github.com/vrtmrz/livesync-bridge/tar.gz/$BRIDGE_COMMIT');
if (!r.ok) throw new Error('download: HTTP ' + r.status);
await Deno.writeFile('/tmp/src.tgz', new Uint8Array(await r.arrayBuffer()));"
tar -xzf /tmp/src.tgz -C "$APP" --strip-components=1
cd "$APP"
# --frozen: exactly the versions and hashes in the commit's deno.lock.
deno install --frozen
touch .installed
echo "livesync-bridge $BRIDGE_COMMIT installed"
