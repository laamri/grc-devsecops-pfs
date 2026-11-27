"""Inspect configuration, full history and every published layer, never an export.

Usage: python scripts/scan_image_secrets.py IMAGE REPORT.json [OLD_IMAGE]
Reports omit candidate values. Nonzero Gitleaks findings require qualification;
nonempty Next.js key fields or recovered old keys are a blocking failure.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

FIELDS = {'encryptionKey', 'previewModeSigningKey', 'previewModeEncryptionKey', 'previewModeId'}
PATTERNS = {
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'credential-assignment': re.compile(
        rb'(?i)(?:secret_key|jwt_secret|aws_secret_access_key|password|api_key)\s*[=:]\s*[\x22\x27]?([^\s\x22\x27,;}{]{8,})'),
    'old-project-marker': re.compile(
        rb'dev_secret_key_auth|votre_cle_secrete(?:_pour_le_dev)?|US06_SYNTHETIC_SECRET_SENTINEL'),
}


def run(*args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def json_fields(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FIELDS:
                yield key, value
            yield from json_fields(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from json_fields(value)


def scan(image, report_path, old_image=None):
    report = {'image': image, 'gitleaksVersion': run('gitleaks', 'version').decode().strip(),
              'layers': [], 'gitleaks': [], 'heuristics': [], 'keyFields': [], 'oldKeyOccurrences': []}
    with tempfile.TemporaryDirectory(prefix='pfs-us08-scan-') as folder:
        temp = Path(folder)
        known = set()
        if old_image:
            old = temp / 'old.tar'
            run('docker', 'save', '-o', str(old), old_image)
            with tarfile.open(old) as outer:
                manifest = json.load(outer.extractfile('manifest.json'))[0]
                for layer_path in manifest['Layers']:
                    with tarfile.open(fileobj=outer.extractfile(layer_path), mode='r|*') as layer:
                        for item in layer:
                            if item.isfile() and item.name in (
                                'app/.next/server/server-reference-manifest.json',
                                'app/.next/server/preview-props.json'):
                                for _, value in json_fields(json.load(layer.extractfile(item))):
                                    if isinstance(value, str) and value:
                                        known.add(value.encode())
            report['oldImage'] = old_image
            report['oldKeyCount'] = len(known)
            assert len(known) == 4, 'Unexpected old key inventory'
            old.unlink()
        archive = temp / 'image.tar'
        run('docker', 'save', '-o', str(archive), image)
        payload = temp / 'payload'
        payload.mkdir()
        locations = {}

        def inspect(data, name, location):
            target = payload / name
            target.write_bytes(data)
            locations[name] = location
            for rule, pattern in PATTERNS.items():
                for match in pattern.finditer(data):
                    report['heuristics'].append({**location, 'rule': rule,
                        'line': data.count(b'\n', 0, match.start()) + 1, 'value': '[MASKED]'})
            if any(key in data for key in known):
                report['oldKeyOccurrences'].append(location)

        inspect(run('docker', 'image', 'inspect', image), 'inspect.txt', {'path': 'docker inspect'})
        inspect(run('docker', 'history', '--no-trunc', '--format', '{{json .}}', image),
                'history.txt', {'path': 'docker history --no-trunc'})
        with tarfile.open(archive) as outer:
            manifests = json.load(outer.extractfile('manifest.json'))
            assert len(manifests) == 1, 'Specify one platform image'
            manifest = manifests[0]
            data = outer.extractfile(manifest['Config']).read()
            assert hashlib.sha256(data).hexdigest() in manifest['Config']
            config = json.loads(data)
            report['configDigest'] = 'sha256:' + hashlib.sha256(data).hexdigest()
            report['historyEntries'] = len(config['history'])
            report['revision'] = config['config'].get('Labels', {}).get('org.opencontainers.image.revision')
            inspect(data, 'config.txt', {'path': 'image configuration'})
            assert len(manifest['Layers']) == len(config['rootfs']['diff_ids'])
            for index, layer_path in enumerate(manifest['Layers'], 1):
                raw = temp / 'layer.raw'
                with outer.extractfile(layer_path) as source, raw.open('wb') as target:
                    shutil.copyfileobj(source, target)
                layer_tar = temp / 'layer.tar'
                with raw.open('rb') as source:
                    compressed = source.read(2) == b'\x1f\x8b'
                with (gzip.open(raw, 'rb') if compressed else raw.open('rb')) as source, layer_tar.open('wb') as target:
                    shutil.copyfileobj(source, target)
                with layer_tar.open('rb') as source:
                    digest = 'sha256:' + hashlib.file_digest(source, 'sha256').hexdigest()
                assert digest == config['rootfs']['diff_ids'][index - 1]
                meta = []
                count = 0
                size = 0
                with tarfile.open(layer_tar) as layer:
                    for item in layer:
                        meta.append({'name': item.name, 'linkname': item.linkname,
                                     'type': str(item.type), 'pax': item.pax_headers})
                        if not item.isfile():
                            continue
                        count += 1
                        size += item.size
                        content = layer.extractfile(item).read()
                        location = {'layer': index, 'diffId': digest, 'path': item.name}
                        inspect(content, f'L{index:02d}_{count:06d}.txt', location)
                        if item.name.startswith('app/.next/') and item.name.endswith('.json'):
                            try:
                                obj = json.loads(content)
                            except (ValueError, UnicodeError):
                                continue
                            for field, value in json_fields(obj):
                                report['keyFields'].append({**location, 'field': field,
                                                            'nonempty': bool(value)})
                inspect(json.dumps(meta).encode(), f'metadata-{index}.txt',
                        {'layer': index, 'path': 'layer metadata'})
                report['layers'].append({'index': index, 'diffId': digest, 'files': count, 'bytes': size})
                raw.unlink()
                layer_tar.unlink()
                print(f'Layer {index}: SHA-256 verified, {count} regular files scanned', flush=True)
        env = os.environ.copy()
        env.pop('GITLEAKS_CONFIG', None)
        env.pop('GITLEAKS_CONFIG_TOML', None)
        output = temp / 'gitleaks.json'
        result = subprocess.run(['gitleaks', 'dir', str(payload), '--redact=100', '--no-banner',
            '--no-color', '--ignore-gitleaks-allow', '--gitleaks-ignore-path', str(temp / 'no-ignore'),
            '--max-target-megabytes', '0', '--max-archive-depth', '5', '--max-decode-depth', '5',
            '--report-format', 'json', '--report-path', str(output)],
            capture_output=True, env=env, cwd=temp)
        assert result.returncode in (0, 1), 'Gitleaks failed; scan incomplete'
        for finding in json.loads(output.read_text(encoding='utf8')):
            name = Path(finding['File']).name
            report['gitleaks'].append({**locations[name], 'rule': finding['RuleID'],
                'line': finding['StartLine'],
                'context': finding['Match'].replace(finding['Secret'], '[MASKED]')})
        report['gitleaksExit'] = result.returncode
        report['blockingKeyFindings'] = (sum(f['nonempty'] for f in report['keyFields'])
                                         + len(report['oldKeyOccurrences']))
        Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf8')
        print(json.dumps({'layers': len(report['layers']), 'historyEntries': report['historyEntries'],
                          'gitleaks': len(report['gitleaks']), 'heuristics': len(report['heuristics']),
                          'blockingKeyFindings': report['blockingKeyFindings']}))
        assert report['blockingKeyFindings'] == 0, 'Embedded runtime key found (value omitted)'


if __name__ == '__main__':
    scan(*sys.argv[1:])
