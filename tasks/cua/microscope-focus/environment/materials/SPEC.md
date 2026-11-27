# Microscope replay contract v1

All distances and Three.js scene coordinates are **millimetres**, +Y follows light, X is transverse, Z is depth. Unrotated cylinder optical axes are +Y. At neutral assembly the landmark origins are body [55,60,0], tube [0,80,0], objective [0,0,0], eyepiece [0,160,0], stage [0,-4.12,0]. Each main object must be a visible nonempty mesh (each local extent >0.1 mm), directly parented to a group named microscope. Preserve editable individual meshes. Reference dimensions: body 12×110×28; tube radius9 length142; stage75×2×55; objective radius7 thickness1; eyepiece radius12 thickness2. Landmark coordinates refer to component centres, and the stage origin is the ideal object plane (the specimen marker is illustrative).

Only `/app/out` is transferred into a fresh verifier; nothing from your running browser or working directory is retained. `microscope/index.html` must work from any local static server. All imports and data must be local. The starter has Three.js 0.169.0 and OrbitControls; retain their MIT notice. Dependencies must be copied under your project. Do not create a build step or require npm at runtime.

`state.json`:
```json
{"schemaVersion":1,"units":"mm","assembly":{"body":[55,60,0],"tube":[0,80,0],"objective":[0,0,0],"eyepiece":[0,160,0],"stage":[0,-4.12,0]},"settings":[{"id":"a","stageOffset":0,"objectiveOffset":0,"eyepieceOffset":0,"sample":"sample_a.png"},{"id":"b","stageOffset":-0.04,"objectiveOffset":0,"eyepieceOffset":1,"sample":"sample_b.png"},{"id":"c","stageOffset":-0.08,"objectiveOffset":0,"eyepieceOffset":-2,"sample":"sample_a.png"}]}
```
Offsets are additive to neutral world Y coordinates. Settings must retain the prescribed values (tolerance 1e-6 mm); legal runtime ranges: stage ±10, objective ±2, eyepiece ±5 mm. Coordinates finite real numbers, never booleans. Duplicate JSON keys and nonfinite constants are rejected. Report at least 100 bytes. `replay.json` is exactly `{"schemaVersion":1,"entry":"microscope/index.html","state":"state.json"}`.

Expose `window.microscope` once ready:

- `scene`: actual Three.js Scene containing the displayed meshes and Line objects.
- `renderer`: actual WebGLRenderer; render after changes.
- `async applyState(state, index=0)`: build/reset clean assembly and select a setting.
- `async setControls({stageOffset?,objectiveOffset?,eyepieceOffset?})`: update selected controls and physical coordinates, optical model, rays and canvas.
- `async setSample(url)`: decode an arbitrary local 1024×1024 PNG and map it using the same optical transform. Do not assume image identity.
- `serialize()`: JSON serializable assembly and settings; setting0 must represent current controls for save/reload.
- `async reset()`: restore the neutral assembly and setting a.
- `optics`: `{objective:{kind,s,v,m},eyepiece:{kind,s,v,m},total,height,orientation}`. Each lens kind is `real`, `virtual`, `infinity`, or `no-finite-image`. Distances signed; magnification unitless. `height` is final signed height of a 0.05 mm transverse object. Orientation `upright`, `inverted` or `undefined`.

Cartesian equation: signed object distance s=objectY-lensY, 1/v-1/s=1/f, m=v/s. Intermediate imageY=objectiveY+v_o. Thus eye object distance=intermediateImageY-eyeY (including virtual objects downstream of the eye). Do not replace this with an absolute distance. Infinity: |s+f|<1e-9 gives v=m=null; |s|<1e-10 gives no-finite-image. If the objective has no finite image, eyepiece s=v=m=null, kind=no-finite-image. If either magnification is null then total=height=null and orientation=undefined. All other outputs must be finite. Near boundaries retain finite values, annotate/display overflow safely; do not place infinite geometry in the scene.

Use actual THREE.Line geometry named `objective_0`, `objective_1`, `eyepiece_0`, `eyepiece_1`: points [object tip, lens intercept, forward outgoing point], in world coordinates through the scene transforms. Two principal rays: parallel incoming (intercept x=h), and lens-centre ray (intercept x=0). Z=0. For virtual images add `objective_virtual_0/1` or `eyepiece_virtual_0/1`, each [lens intercept, backward image point]. Intercepts must fit lens aperture (7/12 mm). For extreme images >1200 mm or infinity you may omit rays and display a status; all three prescribed settings require rays.

Image mapping contract: `<canvas id="image" width="1280" height="720">`, background RGB(16,24,32), centred at (640,360), nearest-neighbour, no smoothing. For finite total transverse m, draw the complete 1024² input with square width=1024*abs(m)*0.006 pixels; rotate 180° if m<0, do not mirror a single axis. Clip to the canvas. This is a calibrated observer view for virtual images, not a physical screen. For |m|>1e5 or nonfinite image, clear the image and show an explicit boundary status. These calibration units do not change the physical scene units.

No scores, exported coordinates or precomputed optics files are accepted as substitutes for the actual runtime. Verifier uses clean browser contexts twice, independent signed thin-lens equations, actual world matrices, ray vertices, unknown samples, and held-out control changes. All must and critical checks must pass, plus at least 80% normal checks. Exactly 15 rubric IDs follow README §4.5 (R01_runtime may add contract diagnostics).

Manifest v1: `{"schemaVersion":1,"units":"mm","assets":[{"path":"...","role":"...","source":"self-authored or upstream URL","license":"CC0-1.0 or MIT"}]}`. Required entries: `microscope/assets/sample_a.png`, `microscope/assets/sample_b.png`, `microscope/vendor/three.module.js`, `microscope/vendor/OrbitControls.js`, `references/front.png`, `references/side.png`, `references/three_quarter.png`, `optics.pdf`. Reference entries describe supplied resources; they need not be copied to out. All additional textures/fonts must also be listed. Use system fonts to avoid font dependencies.
