#!/usr/bin/env bash
# Refresh the pinned copy of razbiram.com's capability profile.
#
# The exporter reads docs/schemas/learncard-target.profile.v1.json to decide which card families
# may leave the tool. That copy is committed on purpose — exports must work offline and Golden runs
# must not depend on a remote file. Updating it is therefore a deliberate act whose diff is
# reviewed, not something that happens silently between two runs.
#
# Usage: scripts/refresh-target-profile.sh [URL]     (default: the production profile)
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

URL="${1:-https://razbiram.com/learncards/profile.v1.json}"
DEST="docs/schemas/learncard-target.profile.v1.json"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

echo "fetching $URL"
if ! curl -fsSL --max-time 20 "$URL" -o "$TMP"; then
  echo "✗ fetch failed — the pinned copy is unchanged." >&2
  exit 1
fi

if ! python3 -c "
import json,sys
d=json.load(open('$TMP'))
caps=d.get('capabilities')
assert isinstance(caps,list) and caps and all(isinstance(c,str) for c in caps), 'no usable capabilities[]'
print('  capabilities:', ', '.join(sorted(caps)))
"; then
  echo "✗ not a usable profile — the pinned copy is unchanged." >&2
  exit 1
fi

if diff -q "$TMP" "$DEST" >/dev/null 2>&1; then
  echo "✓ already up to date"
  exit 0
fi

echo "-- diff --"
diff -u "$DEST" "$TMP" || true
cp "$TMP" "$DEST"
echo "✓ updated $DEST — review the diff above, then commit it on its own."
