"""Test an already built frontend with the published backend 1.0.0; no rebuild/push.

Usage: python scripts/validate_us08_frontend.py IMAGE REPORT.json
Only uniquely named test containers/networks and their anonymous volumes are removed.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ('132415609490.dkr.ecr.eu-north-1.amazonaws.com/pfs-backend@'
           'sha256:7e1f0ab6f82f4a6fde888450d5aac7507f6ff182e965c4720726208af56ca7ba')
MONGO = 'mongo@sha256:d97fea17ccb8d004cd137be8dab54d70d0df11be69c9f422aefe4484c8414ab7'


def run(*args, env=None):
    return subprocess.run(args, check=True, capture_output=True, text=True, env=env).stdout.strip()


def main(image, report_path):
    prefix = 'pfs-us08-' + uuid.uuid4().hex[:10]
    names = []
    run('docker', 'network', 'create', prefix)
    try:
        def start(role, source, *args, command=()):
            name = prefix + '-' + role
            run('docker', 'run', '-d', '--name', name, '--network', prefix,
                *args, source, *command)
            names.append(name)
            return name

        mongo = start('mongo', MONGO)
        for _ in range(90):
            try:
                run('docker', 'exec', mongo, 'mongosh', '--quiet', '--eval',
                    'quit(db.adminCommand({ping:1}).ok ? 0 : 1)')
                break
            except subprocess.CalledProcessError:
                time.sleep(1)
        else:
            raise RuntimeError('Test MongoDB did not start')
        auth = start('auth', BACKEND, command=('uvicorn', 'auth_service.main:app',
                                             '--host', '0.0.0.0', '--port', '8001'))
        task = start('task', BACKEND, '-e', 'PORT=8002', '-e', f'MONGO_URI=mongodb://{mongo}:27017/',
                     command=('uvicorn', 'task_service.main:app', '--host', '0.0.0.0', '--port', '8002'))
        frontend = start('frontend', image, '-p', '127.0.0.1::3000',
                         '-e', f'AUTH_INTERNAL_URL=http://{auth}:8001',
                         '-e', f'TASK_INTERNAL_URL=http://{task}:8002')
        port = run('docker', 'port', frontend, '3000').rsplit(':', 1)[1]
        base = f'http://127.0.0.1:{port}'
        for _ in range(90):
            try:
                for service in ('auth', 'task'):
                    with urllib.request.urlopen(base + f'/api/{service}/health', timeout=2) as response:
                        assert json.load(response)['status'] == 'ok'
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Test frontend/proxies did not start')
        assert run('docker', 'exec', frontend, 'id', '-u') == '1000'
        # Read only booleans from the running container; never print runtime keys.
        check = """
const fs=require('fs'),assert=require('assert/strict');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const p=read('.next/server/preview-props.json'),r=read('.next/prerender-manifest.json');
assert.deepEqual(p,r.preview);
const a=read('.next/server/server-reference-manifest.json');
assert.equal(Buffer.from(a.encryptionKey,'base64').length,32);
for(const k of ['previewModeSigningKey','previewModeEncryptionKey']) assert.equal(p[k].length,64);
for(const file of ['.next/server/preview-props.json','.next/prerender-manifest.json',
 '.next/server/server-reference-manifest.json','.next/server/server-reference-manifest.js'])
 assert.equal(fs.statSync(file).mode & 0o777,0o600);
console.log('Runtime manifests consistent, valid keys, mode 0600');
"""
        runtime = run('docker', 'exec', frontend, 'node', '-e', check)
        with tempfile.TemporaryDirectory(prefix=prefix + '-browser-') as folder:
            tooling = Path(folder)
            npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
            run(npm, 'install', '--prefix', str(tooling), '--no-save', '--no-package-lock',
                '--no-audit', '--no-fund', 'playwright@1.58.2')
            env = os.environ.copy()
            env['PLAYWRIGHT_MODULE'] = str(tooling / 'node_modules/playwright')
            chrome = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
            if chrome.exists():
                env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'] = str(chrome)
            elif not env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
                env['PLAYWRIGHT_BROWSERS_PATH'] = str(tooling / 'browsers')
                run('node', str(tooling / 'node_modules/playwright/cli.js'), 'install', 'chromium', env=env)
            browser = json.loads(run('node', str(ROOT / 'scripts/validate_compose_browser.cjs'),
                                     base, prefix + '-browser-task', env=env))
        image_id = run('docker', 'image', 'inspect', '--format', '{{.Id}}', image)
        assert run('docker', 'inspect', '--format', '{{.Image}}', frontend) == image_id
        result = {'image': image, 'imageId': image_id, 'backend': BACKEND,
                  'runtime': runtime, 'uid': 1000, 'browser': browser}
        Path(report_path).write_text(json.dumps(result, indent=2), encoding='utf8')
        print(json.dumps(result, indent=2))
    finally:
        for name in reversed(names):
            run('docker', 'rm', '-fv', name)
        run('docker', 'network', 'rm', prefix)


if __name__ == '__main__':
    main(*sys.argv[1:])
