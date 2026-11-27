#!/bin/bash
set -euo pipefail
mkdir -p /app/out/microscope
cp -a /solution/microscope/. /app/out/microscope/
cp -a /app/materials/starter/vendor /app/out/microscope/
cp -a /app/materials/samples /app/out/microscope/assets
cp /solution/{state.json,replay.json,report.md,manifest.json} /app/out/
