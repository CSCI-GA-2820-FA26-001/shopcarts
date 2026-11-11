# Shopcarts on local Kubernetes (Story #36)

These manifests deploy the Shopcarts service to the K3D cluster:

- `deployment.yaml`: 2 replicas of `cluster-registry:5000/shopcarts:1.0` with
  readiness and liveness probes on `/health`
- `service.yaml`: a ClusterIP Service on port 8080
- `ingress.yaml`: routes `http://localhost:8080` to the Service through Traefik

The database is the Postgres StatefulSet in [`postgres/`](postgres/README.md) (#38).

Run the commands below from the repository root in the project's Dev Container.

## 1. Create the cluster and push the image

```bash
make cluster          # only if `k3d cluster list` doesn't show nyu-devops
make build
make push
```

`make push` needs `cluster-registry` to resolve to `127.0.0.1`. If it doesn't,
add `127.0.0.1 cluster-registry` to `/etc/hosts`.

## 2. Create the Secrets once

The service reads its credentials from two Secrets. Neither is in Git, because
`make deploy` applies every YAML file under `k8s/`.

`postgres-secret` holds the database password. If it doesn't exist yet, create it
as described in [`postgres/README.md`](postgres/README.md#create-the-password-secret-once).
The Deployment builds `DATABASE_URI` from it, so the password is never written
in a manifest.

`shopcarts-secret` holds the Flask `SECRET_KEY`:

```bash
kubectl --context k3d-nyu-devops -n default get secret shopcarts-secret || \
kubectl --context k3d-nyu-devops -n default create secret generic shopcarts-secret \
  --from-literal=SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex())')"
```

## 3. Deploy

```bash
make deploy
kubectl --context k3d-nyu-devops -n default get pods,service,ingress -l app.kubernetes.io/part-of=shopcarts
```

The shopcarts pods wait for Postgres in an init container, then start. Expect both
to be `Running` with `1/1` Ready.

```bash
curl http://localhost:8080/api/shopcarts
```

After pushing a new image with the same tag, restart the pods to pull it:

```bash
kubectl --context k3d-nyu-devops -n default rollout restart deployment/shopcarts
```

## 4. Verify the acceptance criteria

```bash
bash k8s/verify.sh
```

It checks that the pods are Ready, that `GET /api/shopcarts` works through the ingress,
that a shopcart created with `POST` can be read back from its `Location`, and that
the credentials come from Secrets. It deletes the shopcart it creates. All `PASS`
messages must appear and the script must exit with status 0.

## Troubleshooting

```bash
kubectl --context k3d-nyu-devops -n default describe pod -l app=shopcarts
kubectl --context k3d-nyu-devops -n default logs -l app=shopcarts
kubectl --context k3d-nyu-devops -n default logs -l app=shopcarts -c wait-for-postgres
```

A pod stuck in `CreateContainerConfigError` usually means one of the Secrets is missing.
