"""Safe image preprocessing and inference contract for the Crisp model."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image, UnidentifiedImageError
import tensorflow as tf

CONDITION_CLASSES = ("clean", "stain", "defect")
INPUT_SIZE = (224, 224)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MODEL_SHA256 = "b92588fb3b1662438b1a0df6ba6fc3244872d6c49de859ccb387da63133951d2"


class InferenceError(RuntimeError):
    """An image or model could not be processed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_predictor(model_path: Path) -> "Predictor":
    if not model_path.is_file():
        raise FileNotFoundError(str(model_path))
    actual_hash = sha256_file(model_path)
    if actual_hash != MODEL_SHA256:
        raise InferenceError(f"model SHA-256 mismatch: {actual_hash}")
    model = tf.keras.models.load_model(model_path, compile=False, safe_mode=True)
    return Predictor(model=model, model_sha256=actual_hash)


def preprocess_image(stream: BinaryIO) -> np.ndarray:
    raw = stream.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds byte limit")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("image exceeds pixel limit")
            if image.format not in {"JPEG", "PNG", "BMP", "GIF"}:
                raise ValueError("unsupported image format")
        # Preserve upstream TensorFlow decoding and floating-point resize.
        image = tf.image.decode_image(raw, channels=3, expand_animations=False)
        image = tf.image.resize(image, INPUT_SIZE)
        array = (tf.cast(image, tf.float32) / 255.0).numpy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, tf.errors.InvalidArgumentError) as exc:
        raise ValueError("uploaded file is not a valid image") from exc
    if array.shape != (224, 224, 3) or not np.isfinite(array).all():
        raise ValueError("image preprocessing produced an invalid tensor")
    return array[None, ...]


class Predictor:
    def __init__(self, model: tf.keras.Model, model_sha256: str):
        self.model = model
        self.model_sha256 = model_sha256
        if not isinstance(model.output, dict) or set(model.output) != {"attribute_output", "condition_output"}:
            raise InferenceError("model outputs must be named attribute_output and condition_output")
        shapes = {name: tuple(t.shape) for name, t in model.output.items()}
        if tuple(model.input_shape) != (None, 224, 224, 3):
            raise InferenceError(f"unexpected model input shape: {model.input_shape}")
        if shapes["condition_output"] != (None, 3):
            raise InferenceError("unexpected condition output width")
        if shapes["attribute_output"] != (None, 26):
            raise InferenceError("unsupported attribute output; attribute names are unavailable")

    def predict(self, stream: BinaryIO) -> dict:
        tensor = preprocess_image(stream)
        outputs = self.model(tensor, training=False)
        if not isinstance(outputs, dict) or "condition_output" not in outputs:
            raise InferenceError("model outputs are not named")
        condition = np.asarray(outputs["condition_output"])
        if condition.shape != (1, 3) or not np.isfinite(condition).all():
            raise InferenceError("invalid condition output")
        condition = condition[0]
        if (condition < 0).any() or (condition > 1).any() or not np.isclose(condition.sum(), 1.0, atol=1e-5):
            raise InferenceError("invalid condition probabilities")
        index = int(np.argmax(condition))
        return {
            "model_sha256": self.model_sha256,
            "validation_status": "unvalidated candidate; accuracy not established",
            "condition": {
                "label": CONDITION_CLASSES[index],
                "probabilities": {name: float(value) for name, value in zip(CONDITION_CLASSES, condition)},
            },
            "attributes": [],
            "attribute_status": "omitted: authoritative 26-label names/order are unavailable",
        }
