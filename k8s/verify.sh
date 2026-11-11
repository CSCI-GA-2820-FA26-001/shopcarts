#!/usr/bin/env bash
# Story #36 acceptance test. Checks the deployed service end to end through the ingress.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

# Explicit context/namespace prevent accidentally targeting another cluster.
kc() {
    kubectl --context k3d-nyu-devops --namespace default "$@"
}

kc rollout status deployment/shopcarts --timeout=180s
kc wait --for=condition=Ready pod -l app=shopcarts --timeout=180s
echo "PASS: The shopcarts pods are Running and Ready."

# The ingress can take a few seconds to route to new pods
status=""
for attempt in {1..30}; do
    status="$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/shopcarts" || true)"
    if [[ "$status" = 200 ]]; then
        break
    fi
    sleep 2
done
test "$status" = 200
curl -sf "$BASE_URL/shopcarts" | python3 -c 'import json, sys; assert isinstance(json.load(sys.stdin), list)'
echo "PASS: GET $BASE_URL/shopcarts returns 200 OK with a JSON list."

headers="$(mktemp)"
trap 'rm -f "$headers"' EXIT
created="$(curl -sf -D "$headers" -X POST "$BASE_URL/shopcarts" \
    -H 'Content-Type: application/json' -d '{"user_id": 3636}')"
grep -q '^HTTP/[0-9.]* 201' "$headers"
location="$(grep -i '^location:' "$headers" | tr -d '\r' | awk '{print $2}')"
shopcart_id="$(echo "$created" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
curl -sf "$location" | python3 -c "import json, sys; assert json.load(sys.stdin)['id'] == $shopcart_id"
echo "PASS: POST returns 201 Created and its Location returns shopcart $shopcart_id."
curl -sf -o /dev/null -X DELETE "$location"

# The credentials must come from Secrets, and DATABASE_URI must only reference the password
kc get deployment shopcarts -o jsonpath='{.spec.template.spec.containers[0].env}' \
    | python3 -c '
import json, sys
env = {e["name"]: e for e in json.load(sys.stdin)}
assert "secretKeyRef" in env["POSTGRES_PASSWORD"]["valueFrom"]
assert "secretKeyRef" in env["SECRET_KEY"]["valueFrom"]
assert "$(POSTGRES_PASSWORD)" in env["DATABASE_URI"]["value"]
'
echo "PASS: The database password and secret key come from Kubernetes Secrets."
