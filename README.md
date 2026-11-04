# Crisp real inference

This repository contains the Flask UI and API built from the Crisp source audited at upstream commit `3c88caa1fbcc2ef33dddb6e3d9407bce2844eb24`.

The API loads `project_model_best.keras` once, verifies its SHA-256, converts uploaded images to RGB 224x224 tensors, divides pixels by 255, and returns the model's three-condition softmax output in the source order `clean`, `stain`, `defect`. There is no random or hardcoded fallback.

Model provenance

- Source: `https://github.com/winiman0/crisp`
- Upstream commit: `3c88caa1fbcc2ef33dddb6e3d9407bce2844eb24`
- Selected artifact: `project_model_best.keras` (provisional selection; owner confirmation of canonical artifact is still required)
- SHA-256: `b92588fb3b1662438b1a0df6ba6fc3244872d6c49de859ccb387da63133951d2`
- Runtime: TensorFlow 2.21.0, Keras 3.15.1, Python 3.13+

The artifact has a 26-way attribute output, but the upstream repository does not contain the authoritative attribute names and order. The API therefore omits attribute predictions instead of inventing labels. No accuracy claim is made; an independent labelled holdout and acceptance thresholds are still required.

Run locally

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`. Uploads are processed in memory and are limited to 10 MiB by default (`CRISP_MAX_UPLOAD_BYTES` can lower or raise this limit deliberately).

Verification

```sh
python -m pytest -q
```

The tests include actual model loading and inference, preprocessing shape/range checks, invalid uploads, and Flask endpoint checks. The test result for the implementation was `5 passed`.
