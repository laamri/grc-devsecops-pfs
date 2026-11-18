"""US06: validate the staged Git snapshot, using only disposable Docker resources.
Run from repository root: python scripts/validate_images.py
Stages must be prepared with git add first. No push, prune or existing-container changes.
"""
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
REPORT = {}
PREFIX = 'pfs-us06-' + uuid.uuid4().hex[:8]
CONTAINERS = []
NETWORK = PREFIX
NETWORK_CREATED = False


def run(*args, capture=False, cwd=None):
    result = subprocess.run(args, cwd=cwd or ROOT, check=True,
                            stdout=subprocess.PIPE if capture else None,
                            text=True)
    return result.stdout.strip() if capture else ''


def request(port, path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=payload,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200
        body = response.read().decode()
        return json.loads(body) if path != '/' else body


def start(role, image, internal_port=None, env=None, command=()):
    name = PREFIX + '-' + role
    args = ['docker', 'run', '-d', '--name', name, '--network', NETWORK]
    if internal_port:
        args += ['-p', f'127.0.0.1::{internal_port}']
    for key, value in (env or {}).items():
        args += ['-e', f'{key}={value}']
    run(*args, image, *command, capture=True)
    CONTAINERS.append(name)
    if not internal_port:
        return name, None
    port = int(run('docker', 'port', name, str(internal_port), capture=True).rsplit(':', 1)[1])
    return name, port


def wait_http(port, path):
    for _ in range(90):
        try:
            return request(port, path)
        except Exception:
            time.sleep(1)
    raise RuntimeError(f'HTTP not ready: {port}{path}')


def inspect_image(tag):
    info = json.loads(run('docker', 'image', 'inspect', tag, capture=True))[0]
    assert info['Config']['User'] not in ('', '0', 'root')
    history = run('docker', 'history', '--no-trunc', tag, capture=True)
    assert all(marker not in history for marker in ['SECRET_KEY=', 'dev_secret_key_auth', 'votre_cle_secrete'])
    REPORT[tag] = {'id': info['Id'], 'bytes': info['Size'], 'user': info['Config']['User'],
                   'history_checked': True}
    return info['Id']


def check_files(name, directory):
    archive = directory / (name + '.tar')
    run('docker', 'export', '-o', str(archive), name)
    forbidden = []
    with tarfile.open(archive) as tar:
        for item in tar:
            parts = Path(item.name).parts
            if any(p in ('.git', '.env', '.env.local', '.env.production', '.pytest_cache') for p in parts) or (item.name.startswith(('app/', 'opt/venv/')) and '__pycache__' in parts):
                forbidden.append(item.name)
            if item.isfile() and (item.name.startswith('app/') or item.name.startswith('opt/venv/')):
                if item.size < 2_000_000:
                    content = tar.extractfile(item).read()
                    if item.name.endswith(('.pem', '.key')) and b'PRIVATE KEY-----' in content:
                        forbidden.append(item.name)
                    assert not any(marker in content for marker in
                                   [b'dev_secret_key_auth', b'votre_cle_secrete_pour_le_dev', b'US06_SYNTHETIC_SECRET_SENTINEL'])
    assert not forbidden, forbidden[:10]
    archive.unlink()


def main():
    global NETWORK_CREATED
    with tempfile.TemporaryDirectory(prefix=PREFIX) as temporary:
        clean = Path(temporary)
        run('git', 'checkout-index', '--all', '--prefix=' + clean.as_posix() + '/')
        assert not (clean / 'frontend/node_modules').exists()
        assert not (clean / 'auth_service/venv').exists()
        assert not (clean / '.env').exists()
        run('docker', 'build', '-t', 'pfs-backend:us06', '-f', 'backend/Dockerfile', '.', cwd=clean)
        run('docker', 'build', '-t', 'pfs-frontend:us06', 'frontend', cwd=clean)
        backend = inspect_image('pfs-backend:us06')
        frontend = inspect_image('pfs-frontend:us06')
        # Test tools are installed only in a disposable container, never in the final image.
        for service in ('auth_service', 'task_service'):
            run('docker', 'run', '--rm', '--user', '0', '--mount',
                f'type=bind,source={clean},target=/src,readonly', '-w', f'/src/{service}',
                backend, 'sh', '-c',
                'pip install --no-cache-dir pytest==8.4.2 httpx==0.28.1 flake8==7.3.0 >/dev/null && '
                'flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && '
                'pytest -q -p no:cacheprovider')
        REPORT['api_tests'] = 'Both existing pytest suites and targeted flake8 passed'
        REPORT['frontend_checks'] = 'npm ci, npm run lint and npm run build passed in Docker builder'
        run('docker', 'network', 'create', NETWORK, capture=True)
        NETWORK_CREATED = True
        mongo = PREFIX + '-mongo'
        start('mongo', 'mongo:8.0')
        for _ in range(60):
            try:
                run('docker', 'exec', mongo, 'mongosh', '--quiet', '--eval', 'quit(db.adminCommand({ping:1}).ok ? 0 : 1)', capture=True)
                break
            except subprocess.CalledProcessError:
                time.sleep(1)
        else:
            raise RuntimeError('MongoDB not ready')
        auth, auth_port = start('auth', backend, 8001, {'CORS_ORIGINS': 'https://us06.example.test'},
                                ('uvicorn', 'auth_service.main:app', '--host', '0.0.0.0', '--port', '8001'))
        task, task_port = start('task', backend, 8002,
                               {'PORT': '8002', 'MONGO_URI': f'mongodb://{mongo}:27017/',
                                'CORS_ORIGINS': 'https://us06.example.test'},
                               ('uvicorn', 'task_service.main:app', '--host', '0.0.0.0', '--port', '8002'))
        front, front_port = start('frontend', frontend, 3000)
        assert wait_http(auth_port, '/health') == {'status': 'ok', 'service': 'auth_service'}
        assert wait_http(task_port, '/health') == {'status': 'ok', 'service': 'task_service'}
        assert wait_http(front_port, '/')
        title = PREFIX + '-persistent-task'
        assert request(task_port, '/tasks/', {'title': title, 'status': 'todo'})['title'] == title
        assert {'title': title, 'status': 'todo'} in request(task_port, '/tasks/')
        for name, port in ((auth, auth_port), (task, task_port)):
            req = urllib.request.Request(f'http://127.0.0.1:{port}/health', headers={'Origin': 'https://us06.example.test'})
            with urllib.request.urlopen(req) as response:
                assert response.headers['Access-Control-Allow-Origin'] == 'https://us06.example.test'
        for name in (auth, task, front):
            uid = run('docker', 'exec', name, 'id', '-u', capture=True)
            assert uid != '0'
            for _ in range(30):
                state = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', name, capture=True)
                if state == 'healthy':
                    break
                time.sleep(1)
            assert state == 'healthy'
            check_files(name, clean)
            REPORT[name] = {'uid': uid, 'health': state, 'files_checked': True}
        # Ensure developer tools are absent from the actual runtime environments.
        run('docker', 'exec', auth, 'python', '-c',
            "import importlib.util; assert all(importlib.util.find_spec(x) is None for x in ['pytest','flake8','httpx'])")
        run('docker', 'exec', front, 'node', '-e',
            "for (const x of ['eslint','typescript']) {try {require.resolve(x); process.exit(1)} catch(e) {if(e.code !== 'MODULE_NOT_FOUND') throw e}}")
        assert run('docker', 'inspect', '--format', '{{.Image}}', auth, capture=True) == backend
        assert run('docker', 'inspect', '--format', '{{.Image}}', task, capture=True) == backend
        REPORT['integration'] = 'HTTP 200, service names, shared image ID, Mongo write/read and CORS passed'
        print(json.dumps(REPORT, indent=2))


if __name__ == '__main__':
    try:
        main()
    finally:
        for container in reversed(CONTAINERS):
            subprocess.run(['docker', 'rm', '-fv', container], stdout=subprocess.DEVNULL)
        if NETWORK_CREATED:
            subprocess.run(['docker', 'network', 'rm', NETWORK], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
