#!/usr/bin/env bash
# Sends a signed GitHub push event for BRANCH to the EventListener (#76), to
# check the trigger without pushing. With master, a new PipelineRun of the
# current master commit must start; with any other branch, none must.
# Usage: bash .tekton/events/send-test-push.sh [BRANCH]
set -euo pipefail

branch="${1:-master}"
repo="CSCI-GA-2820-FA26-001/shopcarts"
url="https://$(oc get route el-cd-listener -o jsonpath='{.spec.host}')"
secret="$(oc get secret github-webhook-secret -o jsonpath='{.data.secretToken}' | base64 -d)"
sha="$(git ls-remote "https://github.com/$repo.git" refs/heads/master | cut -f1)"

payload="$(printf '{"ref":"refs/heads/%s","after":"%s","deleted":false,"repository":{"full_name":"%s","clone_url":"https://github.com/%s.git"}}' \
    "$branch" "$sha" "$repo" "$repo")"
signature="sha256=$(printf '%s' "$payload" | openssl dgst -sha256 -hmac "$secret" | sed 's/^.* //')"

echo "Sending a push to $branch at $sha to $url"
curl -sS -X POST "$url" \
    -H 'Content-Type: application/json' \
    -H 'X-GitHub-Event: push' \
    -H "X-Hub-Signature-256: $signature" \
    -d "$payload"
echo
