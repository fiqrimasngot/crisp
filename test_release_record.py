import hashlib
import json

import pytest

from scripts.release_record import record


def prepare(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = json.dumps({'manifests': [{'annotations': {
        'vnd.docker.reference.type': 'attestation-manifest'}}]}).encode()
    (tmp_path / 'manifest.json').write_bytes(manifest)
    (tmp_path / 'project_model_best.keras').write_bytes(b'unit-test-only model fixture')
    digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
    monkeypatch.setenv('DIGEST', digest)
    monkeypatch.setenv('GITHUB_SHA', 'a' * 40)
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    return digest


def test_record_matches_registry_bytes(tmp_path, monkeypatch):
    digest = prepare(tmp_path, monkeypatch)
    record()
    result = json.loads((tmp_path / 'release.json').read_text())
    assert result['image'].endswith('@' + digest)
    assert result['accuracy_validated'] is False
    assert result['source_commit'] == 'a' * 40


@pytest.mark.parametrize('value', ['latest', 'sha256:' + '0' * 64])
def test_record_rejects_bad_or_mismatched_digest(tmp_path, monkeypatch, value):
    prepare(tmp_path, monkeypatch)
    monkeypatch.setenv('DIGEST', value)
    with pytest.raises(AssertionError):
        record()
    assert not (tmp_path / 'release.json').exists()


def test_record_requires_attestations(tmp_path, monkeypatch):
    prepare(tmp_path, monkeypatch)
    manifest = b'{"manifests": []}'
    (tmp_path / 'manifest.json').write_bytes(manifest)
    monkeypatch.setenv('DIGEST', 'sha256:' + hashlib.sha256(manifest).hexdigest())
    with pytest.raises(AssertionError):
        record()
