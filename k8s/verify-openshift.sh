#!/usr/bin/env bash
# Story #65 acceptance test. Checks the service on OpenShift end to end through the Route,
# including that a shopcart survives a restart of the postgres pod.
# Run it after `oc login` and `oc project <your-project>`.
set -euo pipefail

host="$(oc get route shopcarts -o jsonpath='{.spec.host}')"
BASE_URL="${BASE_URL:-https://$host}"
echo "Using $BASE_URL in project $(oc project -q)"

oc rollout status statefulset/postgres --timeout=180s
oc rollout status deployment/shopcarts --timeout=180s
oc wait --for=condition=Ready pod -l app=postgres --timeout=180s
oc wait --for=condition=Ready pod -l app=shopcarts --timeout=180s
echo "PASS: The shopcarts and postgres pods are Running and Ready."

# A new Route can take a few seconds to be admitted by the router
health=""
for attempt in {1..30}; do
    health="$(curl -s "$BASE_URL/health" || true)"
    if [[ "$health" == *'"OK"'* ]]; then
        break
    fi
    sleep 2
done
curl -sf "$BASE_URL/health" | python3 -c 'import json, sys; assert json.load(sys.stdin) == {"status": "OK"}'
echo "PASS: GET $BASE_URL/health returns 200 OK with {\"status\": \"OK\"}."

created="$(curl -sf -X POST "$BASE_URL/api/shopcarts" \
    -H 'Content-Type: application/json' -d '{"user_id": 6565}')"
shopcart_id="$(echo "$created" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
echo "Created shopcart $shopcart_id; restarting the postgres pod"

oc delete pod postgres-0 --wait=true
oc rollout status statefulset/postgres --timeout=180s
oc wait --for=condition=Ready pod/postgres-0 --timeout=180s

# The service's connection pool reconnects on the next requests
found=""
for attempt in {1..15}; do
    found="$(curl -s "$BASE_URL/api/shopcarts/$shopcart_id" | python3 -c 'import json, sys
try:
    print(json.load(sys.stdin).get("id", ""))
except ValueError:
    print("")' || true)"
    if [[ "$found" == "$shopcart_id" ]]; then
        break
    fi
    sleep 2
done
test "$found" = "$shopcart_id"
echo "PASS: GET returns shopcart $shopcart_id after the postgres pod came back."
curl -sf -o /dev/null -X DELETE "$BASE_URL/api/shopcarts/$shopcart_id"
