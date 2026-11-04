"""Synthetic transport/contract fixtures, not labelled accuracy examples."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import tensorflow as tf
from PIL import Image

import inference


def fixture_bytes(mode="RGB", fmt="PNG"):
    # Nonuniform rectangular pixels expose resize rounding/antialias drift.
    pixels = (np.arange(19 * 31 * 3).reshape(19, 31, 3) % 256).astype("uint8")
    image = Image.fromarray(pixels).convert(mode)
    stream = BytesIO()
    image.save(stream, format=fmt)
    return stream.getvalue()


@pytest.mark.parametrize("mode,fmt", [("RGB", "PNG"), ("L", "PNG"), ("RGBA", "PNG"), ("RGB", "JPEG"), ("RGB", "BMP"), ("RGB", "GIF")])
def test_exact_upstream_preprocessing(mode, fmt):
    raw = fixture_bytes(mode, fmt)
    # winiman0/crisp@3c88caa, src/preprocessing/trainpre.py:41-51.
    expected = tf.image.decode_image(raw, channels=3, expand_animations=False)
    expected = tf.cast(tf.image.resize(expected, (224, 224)), tf.float32) / 255.0
    np.testing.assert_array_equal(inference.preprocess_image(BytesIO(raw)), expected.numpy()[None])


def test_hash_mismatch_never_deserializes(tmp_path, monkeypatch):
    path = tmp_path / "model.keras"
    path.write_bytes(b"not the pinned model")
    def forbidden(*args, **kwargs):
        pytest.fail("untrusted model was deserialized")
    monkeypatch.setattr(tf.keras.models, "load_model", forbidden)
    with pytest.raises(inference.InferenceError, match="SHA-256"):
        inference.load_predictor(path)


def test_missing_model(tmp_path):
    with pytest.raises(FileNotFoundError):
        inference.load_predictor(tmp_path / "missing.keras")


def test_loader_uses_safe_inference_mode(monkeypatch):
    calls = []
    def loader(path, **kwargs):
        calls.append(kwargs)
        return ContractModel({})
    monkeypatch.setattr(tf.keras.models, "load_model", loader)
    inference.load_predictor(Path(__file__).parent / "project_model_best.keras")
    assert calls == [{"compile": False, "safe_mode": True}]


@pytest.mark.parametrize("raw", [b"", b"not an image", fixture_bytes()[:40]])
def test_invalid_or_truncated_image(raw):
    with pytest.raises(ValueError):
        inference.preprocess_image(BytesIO(raw))


def test_pixel_limit(monkeypatch):
    monkeypatch.setattr(inference, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ValueError, match="pixel limit"):
        inference.preprocess_image(BytesIO(fixture_bytes()))


def test_byte_limit(monkeypatch):
    monkeypatch.setattr(inference, "MAX_IMAGE_BYTES", 20)
    with pytest.raises(ValueError, match="byte limit"):
        inference.preprocess_image(BytesIO(fixture_bytes()))


@pytest.fixture(scope="module")
def real_predictor():
    return inference.load_predictor(Path(__file__).parent / "project_model_best.keras")


def test_real_inference_repeatable_and_matches_direct_model(real_predictor):
    raw = fixture_bytes()
    first = real_predictor.predict(BytesIO(raw))
    second = real_predictor.predict(BytesIO(raw))
    assert first == second
    direct = real_predictor.model(inference.preprocess_image(BytesIO(raw)), training=False)
    probabilities = first["condition"]["probabilities"]
    assert list(probabilities) == ["clean", "stain", "defect"]
    np.testing.assert_allclose(list(probabilities.values()), direct["condition_output"].numpy()[0], rtol=1e-6)
    assert first["validation_status"] == "unvalidated candidate; accuracy not established"


class ContractModel:
    input_shape = (None, 224, 224, 3)
    output = {"condition_output": SimpleNamespace(shape=(None, 3)), "attribute_output": SimpleNamespace(shape=(None, 26))}
    def __init__(self, result):
        self.result = result
    def __call__(self, tensor, training):
        assert training is False
        return self.result


@pytest.mark.parametrize("result", [{}, {"condition_output": [[float("nan"), 0, 1]]}, {"condition_output": [[-1, 1, 1]]}, {"condition_output": [[0.1, 0.1, 0.1]]}, {"condition_output": [0, 0, 1]}, {"condition_output": [[0, 1]]}])
def test_malformed_outputs_fail_closed(result):
    predictor = inference.Predictor(ContractModel(result), "test-only")
    with pytest.raises(inference.InferenceError):
        predictor.predict(BytesIO(fixture_bytes()))


def test_rejects_unnamed_model():
    model = ContractModel({})
    model.output = []
    with pytest.raises(inference.InferenceError, match="named"):
        inference.Predictor(model, "test-only")


def test_api_model_failure_and_upload_limits(monkeypatch):
    import app as service
    client = service.app.test_client()
    monkeypatch.setattr(service, "_predictor", None)
    monkeypatch.setattr(service, "_predictor_error", RuntimeError("test unavailable"))
    response = client.post("/predict", data={"image": (BytesIO(fixture_bytes()), "image.png")})
    assert response.status_code == 503
    assert "condition" not in response.get_json()
    monkeypatch.setitem(service.app.config, "MAX_CONTENT_LENGTH", 10)
    assert client.post("/predict", data={"image": (BytesIO(fixture_bytes()), "image.png")}).status_code == 413
