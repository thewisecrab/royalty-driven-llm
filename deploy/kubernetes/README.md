# Kubernetes Deployment

Create the token-hash secret before applying the manifests:

```bash
kubectl create namespace rdllm
kubectl -n rdllm create secret generic rdllm-service-secret \
  --from-literal=token_sha256="$RDLLM_SERVICE_TOKEN_SHA256"
kubectl apply -k deploy/kubernetes
```

The deployment runs as non-root, drops Linux capabilities, disables privilege
escalation, uses a read-only root filesystem, mounts a persistent audit-log
volume, and exposes `/healthz` and `/readyz` probes.

`secret.example.yaml` is documentation only. Do not apply it unchanged.
