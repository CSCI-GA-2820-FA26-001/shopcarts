#!/bin/sh
# Apply the manifests with the image built by this PipelineRun, then wait for readiness.
set -eu

fail() {
    printf '%s\n' "$*" >&2
    exit 1
}

[ "$#" -eq 3 ] || fail "Usage: deploy.sh APP_NAME IMAGE_NAME IMAGE_DIGEST"
app_name=$1
image_name=$2
image_digest=$3

case "$app_name" in *[!a-z0-9.-]*|'') fail "Invalid APP_NAME" ;; esac
case "$image_name" in *[!a-zA-Z0-9./:_-]*|'') fail "Invalid IMAGE_NAME" ;; esac
case "$image_digest" in *[!a-z0-9:]*|'') fail "Invalid IMAGE_DIGEST" ;; esac
printf '%s\n' "$app_name" | grep -Eq '^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$' || fail "Invalid APP_NAME"
[ "${#app_name}" -le 253 ] || fail "Invalid APP_NAME"
printf '%s\n' "$image_name" | grep -Eq '^[a-zA-Z0-9][a-zA-Z0-9./:_-]*$' || fail "Invalid IMAGE_NAME"
printf '%s\n' "$image_digest" | grep -Eq '^sha256:[0-9a-f]{64}$' || fail "Invalid IMAGE_DIGEST"

# Remove only a tag on the final path component, preserving any registry port.
image_repository=$image_name
case "${image_repository##*/}" in
    *:*) image_repository=${image_repository%:*} ;;
esac
image_ref="${image_repository}@${image_digest}"
[ -f k8s/deployment.yaml ] || fail "Run deploy.sh from the cloned repository root"

staging_dir=$(mktemp -d "${TMPDIR:-/tmp}/shopcarts-deploy.XXXXXX")
trap 'rm -rf "$staging_dir"' EXIT
trap 'exit 1' HUP INT TERM
cp -R k8s "$staging_dir/manifests"
manifest_dir="$staging_dir/manifests"

# This manifest is the local K3D/Traefik entry point; OpenShift uses the Route from #65.
if [ -f "$manifest_dir/ingress.yaml" ]; then
    ingress_kind=$(oc create --dry-run=client --validate=false -f "$manifest_dir/ingress.yaml" \
        -o 'jsonpath={.kind}')
    if [ "$ingress_kind" = "Ingress" ]; then
        rm "$manifest_dir/ingress.yaml"
    fi
fi

# Never apply credentials or access grants. Those are provisioned separately by #65.
kinds=$(oc create --dry-run=client --validate=false --recursive -f "$manifest_dir" \
    -o 'go-template={{.kind}}{{"\n"}}{{range .items}}{{.kind}}{{"\n"}}{{end}}')
if printf '%s\n' "$kinds" | grep -Eq '^(Secret|Role|RoleBinding|ClusterRole|ClusterRoleBinding|ServiceAccount|Namespace)$'; then
    fail "Keep Secrets and access configuration outside the deploy manifests"
fi

deployment_name=$(oc create --dry-run=client --validate=false -f "$manifest_dir/deployment.yaml" \
    -o 'jsonpath={.metadata.name}')
[ "$deployment_name" = "$app_name" ] || fail "APP_NAME does not match k8s/deployment.yaml"

# Render locally FIRST: the cluster never receives the manifest's K3D image/tag.
oc set image --local -f "$manifest_dir/deployment.yaml" \
    "$app_name=$image_ref" -o yaml > "$staging_dir/deployment.yaml"
mv "$staging_dir/deployment.yaml" "$manifest_dir/deployment.yaml"
oc apply --recursive -f "$manifest_dir"
oc rollout status "deployment/$app_name" --timeout=300s
