#!/bin/bash
# Diagnostic artifact oracle, not evidence of GUI-compliant model completion.
set -euo pipefail
mkdir -p /app/out
for f in fight.blend fight_left.fbx fight_right.fbx render_key_01.png render_key_02.png render_key_03.png render_key_04.png playblast.mp4 manifest.json; do
  cp "/solution/$f" /app/out/
done
