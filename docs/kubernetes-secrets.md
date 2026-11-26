# Kubernetes secret management

The base manifests use External Secrets Operator (ESO) with AWS Secrets
Manager. No password, token, connection string, or private key is committed to
Git. The `ExternalSecret` named `pfs-app-secrets` materializes only the
application keys required by the workloads.

## Installation and first sync

1. Install ESO using its signed Helm chart in the cluster's platform process.
2. Create the IRSA role `pfs-external-secrets` with read-only access to the
   `pfs/prod/app` secret and trust the ESO service account.
3. Review the account/role annotation in `k8s/base/service-accounts.yaml`.
4. Store `MONGO_URI` and `JWT_SECRET` as separate properties of the
   `pfs/prod/app` AWS Secrets Manager secret.
5. Apply `kubectl apply -k k8s/base` and verify `kubectl get externalsecret -n pfs`.

The workloads consume values through `secretKeyRef`; they never receive the
AWS credential or the secret value through Git, a ConfigMap, or a command-line
argument.

## Rotation procedure

Update the property in AWS Secrets Manager, then wait for ESO's one-hour
refresh interval or request a sync by annotating the ExternalSecret. Confirm
the ExternalSecret reports `Ready=True`, restart deployments with
`kubectl rollout restart deployment/auth-service deployment/task-service -n pfs`,
and verify both health endpoints. Record the rotation timestamp and validation
result in the change ticket. Retain the old value only for the approved
rollback window, then revoke it. Never paste either value into Jira or Git.
