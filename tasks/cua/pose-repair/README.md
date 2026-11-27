# pose-repair (README question 4)

Harbor 1.4 budgeted Web3D program repair: 24 globally coupled controls, three
target poses, three views each, an immutable upper-body GLB and local WebGL2
inspector. A broken runnable JS fitter, public client and offline dependencies
are provided. See `instruction.md` for the complete contract and resource limits.

`environment/Dockerfile` copies only public materials, UI and startup script.
The mapping and target controls exist only in the `pose-service` sidecar image
and separate verifier. The service exposes health, target observations and
budgeted query routes, with an append-only ledger and no reset/export/file API.
The internal Docker network has no external route. A service restart reconstructs
counters from its ledger. The ledger must persist for the entire trial.

Task-level artifacts collect `/app/out` from main and `/service-evidence` directly
from the sidecar, using Harbor's service artifact support. The verifier needs
neither the live agent nor a service network: Python independently reconstructs
world positions and rotations from submitted controls and immutable fixture.
Submitted JS then runs as UID 65534 against a fresh loopback service; trusted
fixture directories are root-only. All three cases must pass twice (submitted
controls and independently regenerated controls), including query budgets.

The diagnostic reference fitter uses finite differences and damped Gauss-Newton
on the public observations. It does not read hidden controls or the coupling.
It has no npm dependencies. Target PNGs and the GLB are reproducible with
`authoring/build_materials.py`. All authored assets are CC0.

```sh
docker build -t sci-pose-env environment
docker build -t sci-pose-service environment/service
docker build -t sci-pose-tests tests
# Harbor starts environment/docker-compose.yaml with CONTEXT_DIR set.
```

This task requires a Compose-capable Harbor backend with service artifact
collection (schema 1.4). A `Dockerfile`-only backend cannot enforce its private
service boundary. Runtime UI: run `start-desktop`, visit localhost:8080. Images
are pinned by OCI digest. Actual sanity commands, dependency versions, source
hashes and measured results are in `authoring/calibration/results.md`.
