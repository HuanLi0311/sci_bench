# Offline reproduction

The companion runtime archive contains exact prebuilt base, environment and verifier images, including installed packages.

```sh
docker load -i booth-clearance_runtime-images.tar.gz
```

Image IDs:
- `blender-bench:gui`: `sha256:210d1ac38c39509a58d74df77a21ead78d64396f16cc0a61bc08fc09813cacdf`
- `cua-qc-booth-clearance-env:latest`: `sha256:70f5a5b96a37af6f5bc1c37bb4a71a39d6ee9f8119aa3b394a0eac0b439317a9`
- `cua-qc-booth-clearance-tests:latest`: `sha256:0911b9a99bd354ca003ec0a8c84d73594f9fd5f3850500960429d31ac254ebbc`

Dockerfiles are included for inspection. Future apt rebuilds are not claimed byte-identical;
the supplied prebuilt images are the offline reproducibility path.

From this task directory:

```sh
mkdir -p verification-logs
docker run --rm --network none --cpus 4 --memory 8g --entrypoint bash -v "$PWD/tests:/tests:ro" -v "$PWD/solution:/app/out:ro" -v "$PWD/verification-logs:/logs/verifier" cua-qc-booth-clearance-tests:latest /tests/test.sh /app/out
```

Expected: exit 0, reward.txt=1, metrics 22/22. Infrastructure failures exit 2 with no reward.
GUI-compliance evidence is assessed separately from artifact acceptance.
