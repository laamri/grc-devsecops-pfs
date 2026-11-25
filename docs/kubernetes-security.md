# Kubernetes workload security

The application workloads in `k8s/base/workloads.yaml` implement the
restricted Pod Security Standard profile:

- every pod runs as a non-root UID with `RuntimeDefault` seccomp;
- every container drops all Linux capabilities and disallows privilege
  escalation;
- application and frontend root filesystems are read-only;
- MongoDB receives only its persistent data volume and a temporary `emptyDir`;
- every container has CPU and memory requests and limits;
- application service-account token automounting is disabled.

The namespace labels enforce, audit, and warn on the `restricted` profile. To
verify admission after applying the base manifests, run:

```bash
kubectl apply -f k8s/tests/privileged-pod.yaml
```

The command must be rejected by Pod Security Admission. Delete the test file
if a cluster has a separate admission policy that records rejected objects.
Then verify effective settings with `kubectl get pods -n pfs -o yaml` and
`kubectl describe pod`.
