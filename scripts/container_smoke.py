"""Exercise the packaged model, not a claimed accuracy benchmark."""
from io import BytesIO

from PIL import Image
from app import app
from inference import MODEL_SHA256

image = BytesIO()
Image.new('RGB', (32, 32), (120, 80, 40)).save(image, format='PNG')
image.seek(0)
client = app.test_client()
assert client.get('/').status_code == 200
response = client.post('/predict', data={'image': (image, 'synthetic.png')},
                       content_type='multipart/form-data')
assert response.status_code == 200, response.status_code
result = response.get_json()
assert result['model_sha256'] == MODEL_SHA256
assert set(result['condition']['probabilities']) == {'clean', 'stain', 'defect'}
assert abs(sum(result['condition']['probabilities'].values()) - 1) < 1e-5
assert result['attributes'] == []
assert client.post('/predict', data={}).status_code == 400
print('Packaged real-model inference passed; accuracy is not evaluated.')
