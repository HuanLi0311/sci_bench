# fight-retarget (README question 3)

Harbor 1.4 GUI animation task: two CC0 humanoids, 22 bones each, 1.70 and
1.90 m, a synthetic 300-frame reference fight, four timed contacts, and a
kick/duck. Inputs, reference deliverables, editable authoring sources and a
separate Blender 4.2.3 verifier are included. See `instruction.md` for the
complete acceptance contract.

`authoring/build_fight.py` generates both the starter and diagnostic artifact
oracle from `choreography.py`. `finalize_materials.py` freezes the public bone,
contact and support tables into `tests/spec.json`. The verifier does not import
the animation generator: it measures evaluated world meshes and checks all 300
frames using BVH triangle overlap plus vertex containment, excluding connected
anatomical neighbours. Geometry is convex per authored segment; vertex-depth
measurement is a discrete penetration estimate, not continuous collision
detection between video frames.

The four independent Cycles re-renders reject image substitution and camera
fraud. Right-action time shift and swapped Actions provide animation controls.
Both FBXs are imported into empty Blender scenes. All source textures must be
packed, and only `/app/out` is transferred to the verifier. The oracle copies
pre-authored artifacts; it is explicitly artifact replay, not a cold GUI solve.

Build from the declared contexts:

```sh
docker build -t sci-fight-env environment
docker build -t sci-fight-tests tests
```

For desktop access run `start-desktop` inside the agent container (Xvfb :1,
1920x1080, Xfce, VNC 5900). GUI traces and model pass-rate calibration are not
part of default sanity. See `authoring/calibration/results.md` for actual
commands, image IDs, source hashes, positive/negative results and limitations.
