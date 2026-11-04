"""Record a registry-confirmed image, source and model for GitOps promotion."""
import hashlib
import json
import os
import re
from pathlib import Path


def record():
    digest = os.environ['DIGEST']
    source = os.environ['GITHUB_SHA']
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
    assert re.fullmatch(r'[0-9a-f]{40}', source)
    manifest = Path('manifest.json').read_bytes()
    # buildx --raw writes the exact registry bytes, without an extra newline.
    assert 'sha256:' + hashlib.sha256(manifest).hexdigest() == digest
    index = json.loads(manifest)
    assert any(m.get('annotations', {}).get('vnd.docker.reference.type') ==
               'attestation-manifest' for m in index['manifests'])
    result = {
        'image': 'ghcr.io/fiqrimasngot/crisp@' + digest,
        'digest': digest,
        'source_repository': 'https://github.com/fiqrimasngot/crisp',
        'source_commit': source,
        'model_sha256': hashlib.sha256(Path('project_model_best.keras').read_bytes()).hexdigest(),
        'workflow_run': 'https://github.com/fiqrimasngot/crisp/actions/runs/' + os.environ['GITHUB_RUN_ID'],
        'runner_label': 'gha-crisp',
        'accuracy_validated': False,
    }
    Path('release.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    record()
