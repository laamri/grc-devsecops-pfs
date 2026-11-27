"""Validate US17's rendered application contract (requires kubectl and PyYAML)."""
import subprocess
import yaml

rendered = subprocess.check_output(['kubectl', 'kustomize', 'k8s/base'], text=True)
objects = {(o['kind'], o['metadata']['name']): o for o in yaml.safe_load_all(rendered)}
for name, kind in [('frontend', 'Deployment'), ('auth-service', 'Deployment'),
                   ('task-service', 'Deployment'), ('mongodb', 'StatefulSet')]:
    workload = objects[kind, name]
    assert workload['metadata']['namespace'] == 'pfs'
    pod = workload['spec']['template']
    spec = pod['spec']
    assert spec['automountServiceAccountToken'] is False
    assert ('ServiceAccount', spec['serviceAccountName']) in objects
    assert spec['securityContext']['runAsNonRoot'] is True
    container = spec['containers'][0]
    security = container['securityContext']
    assert security['readOnlyRootFilesystem'] is True
    assert security['allowPrivilegeEscalation'] is False
    assert security['capabilities']['drop'] == ['ALL']
    service = objects['Service', name]
    assert service['spec']['selector'].items() <= pod['metadata']['labels'].items()
    ports = {p['name']: p['containerPort'] for p in container['ports']}
    for port in service['spec']['ports']:
        assert port['targetPort'] in ports
        assert port['port'] == ports[port['targetPort']]
    for probe in ['readinessProbe', 'livenessProbe']:
        if name == 'mongodb':
            command = container[probe]['exec']['command']
            assert command[0] == 'mongosh' and 'ping:1' in command[-1]
        else:
            assert container[probe]['httpGet']['port'] in ports
    if name != 'mongodb':
        assert container['image'].endswith(':sha-150c07ba35cf')
        config = objects['ConfigMap', container['envFrom'][0]['configMapRef']['name']]['data']
        assert int(config['PORT']) == ports['http']
        if name != 'frontend':
            assert container['command'][-1] == '$(PORT)'
            assert config['CORS_ORIGINS'] == 'https://pfs.example.com'
            secret = container['env'][0]['valueFrom']['secretKeyRef']
            assert secret['name'] == 'pfs-app-secrets'
            assert secret['key'] == ('JWT_SECRET' if name == 'auth-service' else 'MONGO_URI')
        else:
            assert config['AUTH_INTERNAL_URL'] == 'http://auth-service:8001'
            assert config['TASK_INTERNAL_URL'] == 'http://task-service:8002'
            init = spec['initContainers'][0]
            assert init['image'] == container['image']
            assert {'name': 'next-runtime', 'mountPath': '/app/.next'} in container['volumeMounts']
    else:
        assert workload['spec']['serviceName'] == name
        assert service['spec']['clusterIP'] == 'None'
        claim = workload['spec']['volumeClaimTemplates'][0]
        assert claim['spec']['resources']['requests']['storage'] == '10Gi'
        assert claim['spec']['accessModes'] == ['ReadWriteOnce']
        assert {'name': claim['metadata']['name'], 'mountPath': '/data/db'} in container['volumeMounts']
    print(f'PASS {kind}/{name}: Service, probes, configuration, security')
assert len([key for key in objects if key[0] == 'ConfigMap']) == 3
for rule in objects['Ingress', 'pfs']['spec']['rules']:
    for path in rule['http']['paths']:
        backend = path['backend']['service']
        assert ('Service', backend['name']) in objects
        assert backend['port']['name'] == 'http'
print('PASS MongoDB 10Gi PVC template and Ingress Service references; namespace pfs')
