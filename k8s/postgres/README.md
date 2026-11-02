# PostgreSQL on local Kubernetes (Story #38)

These manifests run PostgreSQL independently of the Shopcarts API. API deployment
and its `DATABASE_URI` configuration belong to Story #36.

## Prerequisites

Run the commands below from the repository root in the project's Dev Container,
which includes Docker-in-Docker, `k3d`, `kubectl`, and Python. You can use a system
terminal with `docker exec -it -w /app nyu-project bash` when that container is
already running. Run `docker info` inside it to confirm its Docker daemon is ready.

```bash
k3d cluster list
```

If `nyu-devops` does not exist, create it with the existing project target:

```bash
make cluster
```

Reuse an existing healthy cluster; do not delete it to rerun this demo. The target
uses port 8080 inside the Dev Container, so resolve any port conflict first.
All commands below explicitly target context `k3d-nyu-devops`, namespace `default`.

## Create the password Secret once

Check whether the Secret already exists:

```bash
kubectl --context k3d-nyu-devops -n default get secret postgres-secret
```

Only if it reports `NotFound`, generate a local password without printing or
committing it:

```bash
kubectl --context k3d-nyu-devops -n default create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_hex(24))')"
```

The StatefulSet reads `POSTGRES_PASSWORD` with `secretKeyRef`. Do not put real
passwords or a placeholder Secret manifest in Git: `make deploy` recursively
applies YAML files under `k8s/`. A Secret is not a substitute for access controls.

Reuse the same Secret with an existing PVC. `POSTGRES_DB`, `POSTGRES_USER`, and
`POSTGRES_PASSWORD` initialize an **empty** data directory only; changing the
Secret does not change the password already stored in PostgreSQL.

## Deploy and inspect

```bash
kubectl --context k3d-nyu-devops -n default apply --dry-run=server -f k8s/postgres/
kubectl --context k3d-nyu-devops -n default apply -f k8s/postgres/
kubectl --context k3d-nyu-devops -n default rollout status statefulset/postgres --timeout=180s
kubectl --context k3d-nyu-devops -n default get pods,pvc,service -l app=postgres
kubectl --context k3d-nyu-devops -n default get pvc data-postgres-0
```

Expect Pod `postgres-0` to be `Running` with `1/1` Ready, PVC `data-postgres-0` to
be `Bound`, and Service `postgres` to have `CLUSTER-IP` `None` (headless).
The PVC requests 1 GiB from the cluster's default StorageClass; K3D/K3s supplies
the local-path provisioner. No separate PV manifest is needed.

The database is `shopcarts`, the user is `postgres`, and the in-cluster endpoint
is `postgres:5432` in this namespace (or `postgres.default.svc.cluster.local:5432`).
It is not exposed to the host or the public Internet. PostgreSQL 15 matches the
development and CI database version. Its data lives on the PVC, not the Pod's
temporary filesystem. This is a single-instance development database, not an HA
deployment or backup solution.

`make deploy` also discovers these manifests. If using that target, first verify
your current context/namespace and create the Secret there; it may also deploy
other components added in future stories.

## Verify the acceptance criteria

Check authenticated SQL access inside the Pod:

```bash
kubectl --context k3d-nyu-devops -n default exec postgres-0 -- sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database();"'
```

Then run the repeatable acceptance test:

```bash
bash k8s/postgres/verify.sh
```

**This test intentionally deletes and recreates only the local `postgres-0` Pod,
briefly interrupting database connections. Run it only when no one is using this
local test database.** It checks readiness, PVC binding, the headless Service,
and SQL connectivity; inserts a fresh marker into a dedicated test table;
recreates the Pod; and verifies that marker still exists. It removes only its
own marker after success and leaves application tables untouched.

Both `PASS` messages must appear and the script must exit with status 0. This is
the runtime proof required for #38; Python unit tests alone do not test Kubernetes
storage. Do not delete the PVC or the cluster during the persistence test: their
deletion is not covered by the Pod-recreation guarantee and can destroy the data.

For troubleshooting (avoid printing the Secret's contents):

```bash
kubectl --context k3d-nyu-devops -n default describe pod postgres-0
kubectl --context k3d-nyu-devops -n default describe pvc data-postgres-0
kubectl --context k3d-nyu-devops -n default logs postgres-0
```
