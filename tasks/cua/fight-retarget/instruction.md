# Two-character fight retargeting

Use Blender 4.2.3 through the desktop GUI to retarget the supplied synthetic
reference choreography to the two differently proportioned characters.
`/app/materials/reference.mp4` is 10 seconds, H.264, 30 fps, 1280x720: four
punches (three blocks and a body strike), followed by a spinning kick and duck.
`fighters.blend`, two FBX files, `bone_mapping.xlsx` / CSV / JSON,
`action_segments.csv`, `support_phases.json`, `stage.pdf` / JSON and
`LICENSE.txt` are the input pack. All supplied character assets are CC0.

Open `fighters.blend`. Preserve both editable 22-bone hierarchies and their
skin weights. Animate `rig_left` with `Fight_Left` and `rig_right` with
`Fight_Right`, each over frames 1-300. Use metres and 30 fps. Height in the
initial pose must be 1.70 / 1.90 m, each within 2 cm. Bone lengths must match
the mapping table within 1 mm. Initial root separation is 2.4 m +/-5 cm,
with the blue character facing +X and the orange character facing -X.

Preserve four contact events from the segment table within 2 frames. At each
event the attacking hand mesh must be within 3 cm of the specified target
surface. Non-contact character collisions and non-neighbour self-collisions
are forbidden over all 300 frames. At contact only the named mesh pair may
intersect, by at most 1 cm. Ancestor/descendant anatomical segments up to three edges
apart in the published hierarchy are excluded from self-collision, because
their joint surfaces connect. Collision geometry is the evaluated world mesh,
not a helper marker, image or object bounding box.

During every published support interval each foot must drift at most 5 mm
horizontally. Its lowest surface must remain between -1 and +2 mm above the
floor. Each character must stay inside the 6x6 m stage. Keep each character
below 150,000 triangles. Use actual skeletal deformation with editable curves;
shape-key animation and moving a baked mesh instead of the skeleton are not
accepted. All 18 supplied visible segment meshes per character must remain
visible and non-empty. Texture dependencies, if added, must be packed.

Write these regular, non-symlink files to `/app/out` (each <=150 MB; PNGs <=20 MB):

- `fight.blend`, with two independent armatures, skins and Actions.
- `fight_left.fbx`, `fight_right.fbx`: each containing its 22-bone rig and
  animation. An independent re-import must retain the 1-300 action range.
- `render_key_01.png` ... `render_key_04.png`: frames 48, 65, 235 and 300,
  1280x720, from `cam_fixed`. Preserve its orthographic scale 3.8 m,
  location (0, -5.8, 2.25), looking at (0, 0, 0.9).
- `playblast.mp4`: full animation, H.264, 300 frames, 30 fps, 1280x720.
- `manifest.json`: `schemaVersion: 1`, `units: "meters"`, Blender version,
  `assets` entries with path, role, source, license and URL, and the four
  render camera/frame/resolution records. Cite supplied assets as
  `source: "self-authored"`, `license: "CC0-1.0"`.

Evidence PNGs must use Cycles CPU, 64 samples, seed 19, denoise enabled,
Standard view transform. Playblast may use Workbench. The verifier reopens the
scene with auto-execution disabled and without the input pack, measures actual
geometry, imports both FBXs, and independently re-renders every PNG (per-channel
SSIM >=0.94, mean vertical gradient difference <3/255). It shifts the right
Action by six frames: contact-frame SSIM must drop to <=0.98. Swapping the
Actions must make at least one contact exceed 3 cm.
Four decoded video keyframes must also match independent Workbench re-renders
with per-channel SSIM >=0.92; a dimensionally correct unrelated video fails.

All hard requirements and anti-cheat checks must pass; at least 80% of the
quality checks (contact penetration and foot drift) must pass. Reward is binary.
The task allows GUI Blender editing only: do not use a terminal, Python
console, scripts or generated code to author the scene. A reference artifact
oracle is only a diagnostic for the grader and does not count as GUI success.
Do not alter the benchmark, verifier, reward files or hidden reference data.
Do not submit fabricated measurements or pre-rendered substitutes for geometry.

You have 7200 seconds to complete this task.
