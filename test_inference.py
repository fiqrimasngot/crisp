from io import BytesIO

import numpy as np
from PIL import Image

from inference import CONDITION_CLASSES, MODEL_SHA256, load_predictor, preprocess_image


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (32, 32), (120, 80, 40)).save(output, format="PNG")
    return output.getvalue()


def test_preprocess_is_rgb_224_normalized():
    batch = preprocess_image(BytesIO(image_bytes()))
    assert batch.shape == (1, 224, 224, 3)
    assert batch.dtype == np.float32
    assert 0 <= batch.min() <= batch.max() <= 1


def test_real_model_load_and_inference():
    predictor = load_predictor(__import__("pathlib").Path(__file__).parent / "project_model_best.keras")
    result = predictor.predict(BytesIO(image_bytes()))
    assert result["model_sha256"] == MODEL_SHA256
    assert result["condition"]["label"] in CONDITION_CLASSES
    assert set(result["condition"]["probabilities"]) == set(CONDITION_CLASSES)
    assert result["attributes"] == []


def test_invalid_upload_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="valid image"):
        preprocess_image(BytesIO(b"not an image"))
