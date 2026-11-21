# Deploy task (Story #100)

The deploy task uses the installed Red Hat `openshift-client` Task. It applies the
manifests with the digest produced by the build, then waits up to 300 seconds for
`deployment/shopcarts` to become Ready. Any rendering, apply, or rollout error
fails the task.

## Runnable release and full CD integration

The executable `shopcarts-release` Pipeline in `release-pipeline.yaml` accepts a
real, previously built image digest and the matching source workspace. Follow the
[post-build release guide](RELEASE.md) for prerequisites and the start command.
It uses this deployment script and the installed `openshift-client` Task without
clearing the workspace or requiring an unfinished build stage.

The full `cd-pipeline` from #57/#99 still contains only `init`. Its
[deployment integration fragment](integration/deploy-task.yaml) is ready to wire
after the build task (#66) exists. The fragment is not a standalone Kubernetes
resource. The OpenShift deployment prerequisites (#65) are needed by both paths.

To integrate automatic build-to-deploy execution after those dependencies are ready:

1. Confirm the pipeline's build task is called `build` and exposes the
   `IMAGE_DIGEST` result from the pushed image. Adjust the fragment's task/result
   reference if #66 uses a different name. `IMAGE_NAME` is the same full image name
   passed to that build task.
2. Append the fragment to `.tekton/pipeline.yaml` under `spec.tasks`. It reuses
   `APP_NAME`, `IMAGE_NAME`, and `pipeline-workspace` from #57, and runs after build.
3. Verify the cluster resolver can resolve the `openshift-client` Task in the
   `openshift-pipelines` namespace. Check its `SCRIPT` parameter and
   `manifest_dir` workspace with `oc get task openshift-client -n openshift-pipelines -o yaml`.
   The fragment uses the standard `/workspace/manifest_dir` mount. If the installed
   task differs, adapt this binding before the first run.
4. Confirm #65 has provisioned Postgres, the existing `postgres-secret` and
   `shopcarts-secret`, an OpenShift Route, and the PipelineRun service account's
   required namespace permissions. This script neither creates credentials nor
   changes RBAC. `k8s/deployment.yaml` must name both the Deployment and application
   container as `APP_NAME` (currently `shopcarts`).
5. Apply the top-level Tekton resources with `oc apply -f .tekton/` and start the
   completed `cd-pipeline`. Do not use recursive apply on the
   `.tekton/integration/` examples.

## Deployment behavior

`.tekton/scripts/deploy.sh APP_NAME IMAGE_NAME IMAGE_DIGEST` runs from the cloned
repository root. It validates the argument syntax, preserves a registry port when
removing an image tag, and deploys `repository@sha256:<digest>`. A tag such as
`latest` is never used as the rollout target.

The script copies `k8s/` to a temporary directory and replaces the application
image locally before applying any resource. The source checkout is unchanged.
It applies nested manifests such as `k8s/postgres/`, keeps any Route manifest, and
omits `k8s/ingress.yaml` only when that document is a Kubernetes Ingress (the local
K3D/Traefik entry point). OpenShift access uses the Route provisioned by #65.

Secrets, RBAC objects, ServiceAccounts, and Namespaces are rejected if present in
the deployment manifests; their existing cluster state is left alone. Secrets
must be provisioned outside the apply directory. The deployment waits for
Postgres through its existing init container, then the task waits for the
Deployment's readiness probes to succeed.

The catalog Task accepts a shell `SCRIPT`; it does not expose arbitrary argument
or environment parameters. Both pipeline bindings therefore treat the script and
application/image parameters as trusted pipeline configuration, and the digest
as output of a trusted build. Do not expose these parameters as
unvalidated, free-form input from an untrusted webhook. The shell script's syntax
checks validate its received arguments; they do not make Tekton's earlier textual
substitution into `SCRIPT` safe for arbitrary shell text.

## Verification

Run the command-boundary tests without a cluster:

```sh
python -m unittest discover -s tests/tekton -p 'test_deploy.py' -v
```

They verify the exact build digest is rendered before apply, registry ports are
preserved, nested manifests and the Route remain included, K3D ingress is omitted,
credentials/access manifests are rejected, and render/apply/rollout failures
propagate. These tests use a fake `oc`; they do not prove OpenShift permissions,
image pull access, or cluster readiness.

Run `shopcarts-release` to validate deployment of an existing image and verify
that the Deployment uses the supplied digest and completes its rollout. A denied
apply or failed rollout must fail the run.

The final full-CD integration check on the team's OpenShift project is a PipelineRun
whose build pushes an image digest, whose deploy task updates the Deployment to
that digest, and whose rollout succeeds. A denied apply or failed rollout must
mark the run Failed and prevent the downstream BDD task from running. A post-build
release run alone does not verify automatic ordering after #66's build stage.

Reference: [Red Hat openshift-client task and cluster resolver](https://docs.redhat.com/en/documentation/red_hat_openshift_pipelines/1.21/html/creating_cicd_pipelines/remote-pipelines-tasks-resolvers).
