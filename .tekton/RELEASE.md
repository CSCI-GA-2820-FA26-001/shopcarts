# Executable post-build pipeline

`release-pipeline.yaml` installs the `shopcarts-release` Pipeline. It deploys a
real, previously built image by digest using the same deployment script and
`openshift-client` Task as the full CD pipeline's deploy stage. It does not invent
a successful build, run `init`, or erase the source workspace.

## Inputs and prerequisites

- An image has already been built and pushed to a registry accessible from the
  cluster. Use its actual `sha256:...` digest as `IMAGE_DIGEST` and its full
  registry/repository image name as `IMAGE_NAME`.
- The shared PVC contains the matching source revision at its root, including
  `k8s/` and `.tekton/scripts/deploy.sh`. The manifests and image must come from
  the same revision. Do not let another pipeline clear or overwrite this PVC
  while the release is running.
- The OpenShift deployment prerequisites from #65 exist: Postgres configuration,
  provisioned Secrets, Route, registry access, and an existing service account
  permitted to apply the deployment resources in this namespace.
- The cluster resolver can read the installed `openshift-client` Task from
  `openshift-pipelines`. Its interface must include `SCRIPT` and `manifest_dir`.

Apply the executable definition:

```sh
oc apply -f .tekton/release-pipeline.yaml
```

Set `IMAGE_NAME`, `IMAGE_DIGEST`, `SOURCE_PVC`, and `PIPELINE_SERVICE_ACCOUNT` to
the values from the completed build and the configured project, then start it:

```sh
tkn pipeline start shopcarts-release \
  --param APP_NAME=shopcarts \
  --param IMAGE_NAME="$IMAGE_NAME" \
  --param IMAGE_DIGEST="$IMAGE_DIGEST" \
  --workspace name=pipeline-workspace,claimName="$SOURCE_PVC" \
  --serviceaccount "$PIPELINE_SERVICE_ACCOUNT" \
  --showlog
```

The Deployment must use the supplied digest and finish its rollout before the
PipelineRun succeeds. Rendering, apply, and rollout errors fail the run. This
catalog Task substitutes parameters into a shell `SCRIPT`; supply trusted build
configuration, not unvalidated webhook text.

## Full CD integration remains separate

The existing `cd-pipeline` skeleton still lacks clone, lint, unit-test, and build
stages. This post-build Pipeline makes the deployment portion executable without
implementing teammates' stories or referencing a nonexistent `build` task.

When #66 supplies the `build` stage and its `IMAGE_DIGEST` result, integrate
`integration/deploy-task.yaml` into `cd-pipeline.spec.tasks`. That version runs
after `build` and obtains the digest from `$(tasks.build.results.IMAGE_DIGEST)`.
The final acceptance check for automatic build-to-deploy ordering must run on
that full pipeline; a successful post-build run alone does not prove it.

Existing command-boundary tests remain available with
`python -m unittest discover -s tests/tekton -p 'test_deploy.py' -v`. They do not
replace a real Tekton PipelineRun against the target cluster.
