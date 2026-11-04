def test_home_and_invalid_upload():
    from app import app

    client = app.test_client()
    assert client.get("/").status_code == 200
    response = client.post("/predict", data={})
    assert response.status_code == 400


def test_api_runs_real_model():
    from app import app
    from test_inference import image_bytes

    from io import BytesIO
    response = app.test_client().post(
        "/predict",
        data={"image": (BytesIO(image_bytes()), "sample.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["model_sha256"]
    assert payload["attributes"] == []
