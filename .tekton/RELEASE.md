# Executable post-build pipeline

`release-pipeline.yaml` installs the `shopcarts-release` Pipeline with two real
stages: `deploy`, then `bdd`. It consumes a previously built image and its matching
source checkout. It does not invent a successful build, run `init`, or erase the
source workspace. A failed deploy prevents BDD from starting; a failed scenario
fails the PipelineRun.

## Inputs and prerequisites

- An image has already been built and pushed to a registry accessible from the
  cluster. Use its actual `sha256:...` digest as `IMAGE_DIGEST` and its full
  registry/repository image name as `IMAGE_NAME`.
- The shared PVC contains the matching source revision at its root, including
  `k8s/`, `.tekton/scripts/`, `Pipfile`, `Pipfile.lock`, and `features/`. The
  manifests, tests, and image must come from the same revision. Do not let another
  pipeline clear or overwrite this PVC while the release is running.
- The OpenShift deployment prerequisites from #65 exist: Postgres configuration,
  provisioned Secrets, Route, registry access, and an existing service account
  permitted to apply the deployment resources in this namespace.
- The cluster resolver can read the installed `openshift-client` Task from
  `openshift-pipelines`. Its interface must include `SCRIPT` and `manifest_dir`.
- `BASE_URL` is the HTTP/HTTPS Route URL of this isolated test deployment.
  **The BDD fixtures delete shopcarts. Do not target shared demo or production data.**

Apply both executable definitions:

```sh
oc apply -f .tekton/tasks.yaml -f .tekton/release-pipeline.yaml
```

Set `IMAGE_NAME`, `IMAGE_DIGEST`, `BASE_URL`, `SOURCE_PVC`, and
`PIPELINE_SERVICE_ACCOUNT` to the values from the completed build and configured
project, then start it:

```sh
tkn pipeline start shopcarts-release \
  --param APP_NAME=shopcarts \
  --param IMAGE_NAME="$IMAGE_NAME" \
  --param IMAGE_DIGEST="$IMAGE_DIGEST" \
  --param BASE_URL="$BASE_URL" \
  --workspace name=pipeline-workspace,claimName="$SOURCE_PVC" \
  --serviceaccount "$PIPELINE_SERVICE_ACCOUNT" \
  --showlog
```

The Deployment must use the supplied digest and finish its rollout before BDD
starts. The `behave` Task receives `BASE_URL` as an environment variable and runs
the existing browser suite. Rendering, apply, rollout, dependency-installation,
and scenario failures propagate to the PipelineRun. The catalog deployment Task
substitutes parameters into a shell `SCRIPT`; supply trusted build configuration,
not unvalidated webhook text.

## Full CD integration remains separate

The existing `cd-pipeline` skeleton still lacks clone, lint, unit-test, and build
stages. This post-build Pipeline makes deploy-to-BDD execution available without
implementing teammates' stories or referencing a nonexistent `build` task.

When #66 supplies the `build` stage and its `IMAGE_DIGEST` result, integrate
`integration/deploy-task.yaml` and `integration/bdd-task.yaml` into
`cd-pipeline.spec.tasks`. The deploy stage then runs after `build` and obtains
the digest from `$(tasks.build.results.IMAGE_DIGEST)`; BDD runs after deploy.
The final acceptance check for automatic build-to-deploy-to-BDD ordering must run
on that full pipeline; a successful post-build run alone does not prove it.

Existing script tests remain available with
`python -m unittest discover -s tests/tekton -v`. Real Tekton validation must also
confirm a successful deploy-to-BDD run, that deployment failure skips BDD, and
that a failing scenario marks the PipelineRun Failed. A local Kubernetes smoke
test does not establish OpenShift Route networking, security policy, or the
installed catalog Task's compatibility.
