"""Validate the staged US07 snapshot with a unique disposable Compose project.

Run after staging: python scripts/validate_compose.py
Uses Docker Compose, Python, Node/npm and a pinned test Chromium.
Only the project's own test volumes are removed at the very end.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None, capture=False):
    result = subprocess.run(args, cwd=cwd, env=env, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def http(base, path, data=None, status=200):
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(base + path, data=body,
                                     headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.code == status, (path, response.code)
        text = response.read().decode()
        return json.loads(text) if path.startswith('/api/') else text


def main():
    project = 'pfs-us07-' + uuid.uuid4().hex[:10]
    report = {'project': project}
    # Snapshot all pre-existing resources to verify that cleanup leaves them intact.
    old_containers = run('docker', 'ps', '-aq', capture=True).splitlines()
    old_volumes = run('docker', 'volume', 'ls', '-q', capture=True).splitlines()
    old_states = {name: json.loads(run('docker', 'inspect', name, capture=True))[0]['State']
                  for name in old_containers}
    with tempfile.TemporaryDirectory(prefix=project) as folder:
        clean = Path(folder)
        run('git', 'checkout-index', '--all', '--prefix=' + clean.as_posix() + '/')
        assert not any((clean / path).exists() for path in
                       ('.env', 'frontend/node_modules', 'frontend/.env.local', 'task_service/venv'))
        env = os.environ.copy()
        for key in ('FRONTEND_PORT', 'COMPOSE_IMAGE_TAG', 'COMPOSE_MONGO_URI',
                    'CORS_ORIGINS', 'COMPOSE_FILE', 'COMPOSE_PROJECT_NAME',
                    'COMPOSE_PROFILES', 'COMPOSE_ENV_FILES'):
            env.pop(key, None)
        env['COMPOSE_DISABLE_ENV_FILE'] = 'true'
        prefix = ['docker', 'compose', '-p', project, '-f', 'docker-compose.yml']

        def compose(*args, capture=False):
            return run(*prefix, *args, cwd=clean, env=env, capture=capture)

        config = json.loads(compose('config', '--format', 'json', capture=True))
        assert set(config['services']) == {'frontend', 'auth', 'task', 'mongo'}
        assert config['services']['frontend']['ports'][0]['published'] == '3000'
        assert config['services']['task']['environment']['MONGO_URI'] == 'mongodb://mongo:27017/'
        for service in ('auth', 'task', 'mongo'):
            assert not config['services'][service].get('ports')
        assert config['networks']['data']['internal'] is True
        assert 'build' not in config['services']['task']
        # Only tag/host-port differ in the isolated test; application defaults stay intact.
        env.update(FRONTEND_PORT='0', COMPOSE_IMAGE_TAG=project)
        attempted = False
        try:
            attempted = True
            compose('up', '-d', '--wait', '--wait-timeout', '180')

            def check_stack():
                ids = {service: compose('ps', '-q', service, capture=True)
                       for service in ('frontend', 'auth', 'task', 'mongo')}
                states = {service: json.loads(run('docker', 'inspect', identifier, capture=True))[0]
                          for service, identifier in ids.items()}
                assert all(item['State']['Health']['Status'] == 'healthy' for item in states.values())
                assert states['auth']['Image'] == states['task']['Image']
                assert len(states['frontend']['NetworkSettings']['Networks']) == 1
                assert len(states['auth']['NetworkSettings']['Networks']) == 1
                assert len(states['task']['NetworkSettings']['Networks']) == 2
                assert len(states['mongo']['NetworkSettings']['Networks']) == 1
                for service in ('frontend', 'auth', 'task'):
                    assert run('docker', 'exec', ids[service], 'id', '-u', capture=True) != '0'
                port = compose('port', 'frontend', '3000', capture=True).rsplit(':', 1)[1]
                base = 'http://127.0.0.1:' + port
                return states, base

            states, base = check_stack()
            report['frontendAddress'] = base
            report['backendImageId'] = states['auth']['Image']
            report['health'] = {name: state['State']['Health']['Status'] for name, state in states.items()}
            report['auth'] = http(base, '/api/auth/health')
            report['task'] = http(base, '/api/task/health')
            assert report['auth'] == {'status': 'ok', 'service': 'auth_service'}
            assert report['task'] == {'status': 'ok', 'service': 'task_service'}
            assert http(base, '/')
            title = project + '-http-persistence'
            report['created'] = http(base, '/api/task/tasks', {'title': title, 'status': 'todo'})
            assert report['created']['id'] and report['created']['title'] == title
            task = {'title': title, 'status': 'todo'}
            assert task in http(base, '/api/task/tasks')
            http(base, '/api/unknown/health', status=404)
            http(base, '/api/task/not-allowed', status=404)
            http(base, '/api/auth/health', {}, status=405)
            http(base, '/api/task/tasks', {}, status=422)

            # Exercise the actual React UI, not just the proxy endpoints.
            tooling = clean / '.test-browser'
            npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
            assert npm, 'Node/npm required for browser validation'
            run(npm, 'install', '--prefix', str(tooling), '--no-save', '--no-package-lock',
                '--no-audit', '--no-fund', 'playwright@1.58.2')
            browser_env = os.environ.copy()
            browser_env['PLAYWRIGHT_MODULE'] = str(tooling / 'node_modules/playwright')
            executable = browser_env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
            if not executable:
                browser_env['PLAYWRIGHT_BROWSERS_PATH'] = str(tooling / 'browsers')
                run('node', str(tooling / 'node_modules/playwright/cli.js'), 'install', 'chromium', env=browser_env)
            browser = run('node', str(clean / 'scripts/validate_compose_browser.cjs'),
                          base, project + '-browser-task', env=browser_env, capture=True)
            report['browser'] = json.loads(browser)

            volume = next(mount['Name'] for mount in states['mongo']['Mounts'] if mount['Destination'] == '/data/db')
            compose('down')  # Intentionally keep the named volume during the persistence test.
            run('docker', 'volume', 'inspect', volume, capture=True)
            compose('up', '-d', '--wait', '--wait-timeout', '180')
            _, base = check_stack()
            after = http(base, '/api/task/tasks')
            assert task in after
            assert {'title': project + '-browser-task', 'status': 'todo'} in after
            report['persistedAfterDownUp'] = after
            report['volume'] = volume
            report['proxyNegativeTests'] = '404 unknown service/path; 405 health POST; 422 invalid task'
            report['frontendValidation'] = 'npm ci + npm run lint + npm run build in Docker builder'
        finally:
            if attempted:
                # This project name is unique to this run. No pre-existing resources are targeted.
                compose('down', '-v')
        for identifier in old_containers:
            assert json.loads(run('docker', 'inspect', identifier, capture=True))[0]['State'] == old_states[identifier]
        remaining_volumes = run('docker', 'volume', 'ls', '-q', capture=True).splitlines()
        assert set(old_volumes).issubset(remaining_volumes)
        report['preExistingResourcesPreserved'] = True
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
