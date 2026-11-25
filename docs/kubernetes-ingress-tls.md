# Ingress and TLS

`k8s/base/ingress.yaml` exposes the frontend and both API services through the
NGINX Ingress Controller at `pfs.example.com`. The API paths are rewritten to
the FastAPI service roots:

- `/api/auth/...` → `auth-service:8001`;
- `/api/task/...` → `task-service:8002`;
- all other paths → `frontend:3000`.

The Ingress forces HTTP to HTTPS and uses the `pfs-tls` Secret issued by
cert-manager. The checked-in issuer uses Let's Encrypt staging so validation
does not consume production certificate quota. After DNS and HTTP-01 handling
are verified, change the ACME endpoint and issuer reference to the approved
production issuer through a reviewed environment overlay.

## Test procedure

1. Install the NGINX Ingress Controller and cert-manager through the cluster
   platform process.
2. Replace `pfs.example.com` and the issuer email with the approved test
   hostname and team address. Create an A/AAAA record pointing to the Ingress
   load balancer.
3. Apply `kubectl apply -k k8s/base` and wait for
   `kubectl get certificate pfs-tls -n pfs` to report `Ready=True`.
4. Confirm `curl -I http://pfs.example.com/` returns a 308/301 redirect and
   `curl -I https://pfs.example.com/` returns HTTP 200.
5. Validate `/api/auth/health` and `/api/task/health` over HTTPS and record the
   certificate chain and response codes in the deployment evidence.
