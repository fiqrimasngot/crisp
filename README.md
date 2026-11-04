# Crisp real inference

This repository contains the Flask UI and API built from the Crisp source audited at upstream commit `3c88caa1fbcc2ef33dddb6e3d9407bce2844eb24`.

The API loads `project_model_best.keras` once, verifies its SHA-256, decodes uploaded images with TensorFlow into RGB, resizes to 224x224 with TensorFlow's default bilinear resize, divides pixels by 255, and returns the model's three-condition softmax output in the source order `clean`, `stain`, `defect`. There is no random or hardcoded fallback. Pillow only checks image headers and dimensions; it does not resize or decode pixels for inference.

Model provenance

- Source: `https://github.com/winiman0/crisp`
- Upstream commit: `3c88caa1fbcc2ef33dddb6e3d9407bce2844eb24`
- Selected artifact: `project_model_best.keras` (provisional selection; owner confirmation of canonical artifact is still required)
- SHA-256: `b92588fb3b1662438b1a0df6ba6fc3244872d6c49de859ccb387da63133951d2`
- Runtime: TensorFlow 2.21.0, Keras 3.15.1, Python 3.13+
- Preprocessing reference: `src/preprocessing/trainpre.py:30-53` at the upstream commit above. No EXIF rotation, augmentation, antialiasing or extra model normalization is added.
- Condition order reference: `src/backend/inference.py:12-16` and `src/preprocessing/trainpre.py:21` at that commit.
- Upstream inference names `project_model.keras`, not the selected `project_model_best.keras`. This selection remains provisional. Loading uses `compile=False, safe_mode=True` to avoid restoring training state and unsafe deserialization; inference uses `training=False`, as upstream does.

The artifact has a 26-way attribute output, but the upstream repository does not contain the authoritative attribute names and order. The API therefore omits attribute predictions instead of inventing labels. No accuracy claim is made; an independent labelled holdout and acceptance thresholds are still required.

Run locally

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`. Keep this service internal-only; it has no authentication. Uploads are processed in memory. The HTTP request limit defaults to 10 MiB (`CRISP_MAX_UPLOAD_BYTES`). Independently, the decoder rejects files over 10 MiB or 16 million pixels before decoding. Only PNG, JPEG, BMP and GIF are supported; GIF uses its first frame, as upstream does.

Verification

```sh
python -m pytest -q
```

The tests include actual model loading and repeated inference, exact upstream preprocessing parity for nonuniform RGB/grayscale/RGBA PNG, JPEG, BMP and GIF fixtures, missing/tampered model rejection, named output contracts, invalid probabilities, upload limits, and Flask endpoint checks. Synthetic fixtures exercise the code, not detector accuracy. No fixture carries an invented clean/stain/defect ground-truth label.

The candidate artifact and its source are verified locally, but owner confirmation of the canonical model, authoritative attribute labels, and an independent labelled holdout with acceptance thresholds remain external release gates. Every successful prediction reports `validation_status`; neither tests nor model probabilities establish production accuracy. Source/test completion is not deployment acceptance.
