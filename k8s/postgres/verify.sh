#!/usr/bin/env bash
# Story #38 acceptance test. Recreates only the local test Postgres Pod.
set -euo pipefail

# Explicit context/namespace prevent accidentally targeting another cluster.
kc() {
    kubectl --context k3d-nyu-devops --namespace default "$@"
}

sql() {
    kc exec postgres-0 -- sh -c \
        'PGPASSWORD="$POSTGRES_PASSWORD" exec psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -Atc "$1"' \
        sh "$1"
}

kc rollout status statefulset/postgres --timeout=180s
kc wait --for=condition=Ready pod/postgres-0 --timeout=180s
test "$(kc get pvc data-postgres-0 -o jsonpath='{.status.phase}')" = Bound
test "$(kc get service postgres -o jsonpath='{.spec.clusterIP}')" = None
test "$(sql 'SELECT current_database();')" = shopcarts
echo "PASS: Postgres is Ready, the PVC is Bound, and shopcarts accepts queries."

# Use a dedicated table, never the application's tables. A fresh marker ensures
# an old row cannot produce a false pass when this check is run again.
marker="story38-$(date +%s)-${RANDOM}"
sql "CREATE TABLE IF NOT EXISTS story38_persistence_check (marker TEXT PRIMARY KEY);"
sql "INSERT INTO story38_persistence_check (marker) VALUES ('$marker');"
original_uid="$(kc get pod postgres-0 -o jsonpath='{.metadata.uid}')"
echo "Recreating local test Pod postgres-0; its PVC is retained."
kc delete pod postgres-0 --wait=true --timeout=120s

# Wait for a different Pod UID before checking readiness; the replacement may
# not exist immediately after deletion and StatefulSet status can briefly lag.
replacement_uid=""
for attempt in {1..60}; do
    replacement_uid="$(kc get pod postgres-0 -o jsonpath='{.metadata.uid}' 2>/dev/null || true)"
    if [[ -n "$replacement_uid" && "$replacement_uid" != "$original_uid" ]]; then
        break
    fi
    sleep 2
done
test -n "$replacement_uid"
test "$replacement_uid" != "$original_uid"
kc wait --for=condition=Ready pod/postgres-0 --timeout=180s
test "$(kc get pvc data-postgres-0 -o jsonpath='{.status.phase}')" = Bound
# A headless Service's DNS cache can briefly contain the old Pod IP.
saved_marker=""
for attempt in {1..30}; do
    saved_marker="$(sql "SELECT marker FROM story38_persistence_check WHERE marker = '$marker';" 2>/dev/null || true)"
    if [[ "$saved_marker" = "$marker" ]]; then
        break
    fi
    sleep 2
done
test "$saved_marker" = "$marker"
echo "PASS: The test row survived Pod replacement."
sql "DELETE FROM story38_persistence_check WHERE marker = '$marker';"
