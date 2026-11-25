#!/usr/bin/env bash
# Authoring helper: rebuild the chair and print the pose report.
set -e
cd "$(dirname "$0")/.."
docker run --rm -v "$PWD":/task cua-crate-env:dev bash -lc \
  'cd /task && blender -b -P authoring/build_chair.py -- /task/solution /task/environment/materials >/dev/null 2>&1 && blender -b /task/solution/folding_chair.blend -P /task/authoring/check_pose.py'
