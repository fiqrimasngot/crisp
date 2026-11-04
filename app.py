"""Flask UI and API for Crisp's pinned Keras model."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from inference import InferenceError, load_predictor

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("CRISP_MODEL_PATH", BASE_DIR / "project_model_best.keras"))
MAX_UPLOAD_BYTES = int(os.environ.get("CRISP_MAX_UPLOAD_BYTES", 10 * 1024 * 1024))

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
_predictor = None
_predictor_error: Exception | None = None


def predictor():
    global _predictor, _predictor_error
    if _predictor is None and _predictor_error is None:
        try:
            _predictor = load_predictor(MODEL_PATH)
        except Exception as exc:  # surface a clear 503, never fake a result
            _predictor_error = exc
    if _predictor_error is not None:
        raise InferenceError(f"model unavailable: {_predictor_error}") from _predictor_error
    return _predictor


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/predict")
def predict():
    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return jsonify(error="image upload is required"), 400
    try:
        payload = predictor().predict(upload.stream)
    except InferenceError as exc:
        return jsonify(error=str(exc)), 503
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(payload)


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error=f"image exceeds {MAX_UPLOAD_BYTES} bytes"), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
