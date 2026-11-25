#!/usr/bin/env bash
# Extract 8 evenly spaced frames per view from the two videos.
set -euo pipefail
cd "$(dirname "$0")/../environment/materials"
mkdir -p frames
for v in front side; do
  for i in 0 1 2 3 4 5 6 7; do
    t=$(python3 -c "print(round($i * 2.9 / 7, 2))")
    ffmpeg -y -loglevel error -ss "$t" -i "videos/$v.mp4" -frames:v 1 "frames/${v}_0$i.jpg"
  done
done
ls frames | wc -l
