# Deploy and BDD integration validation

Validated on November 21, 2026 using a disposable K3D Kubernetes v1.31.5 cluster
and Tekton Pipelines v1.0.0. The image was built from the repository Dockerfile
and pushed to an isolated local registry. PostgreSQL and Shopcarts were deployed
into a test-only namespace with temporary credentials and namespace-scoped access.

| Check | Observed result |
| --- | --- |
| Apply the committed deploy-only `shopcarts-release` Pipeline | Accepted by the Tekton webhook |
| Run `release-deploy-only` | Succeeded; Deployment rollout completed |
| Read the Deployment's actual container image | Matched the pushed repository and SHA-256 digest exactly |
| Deploy with a mismatched `APP_NAME` | Deploy failed before apply |
| Same failure with downstream BDD configured | PipelineRun failed; BDD was skipped and no BDD TaskRun was created |
| Run the combined `release-success-v2` PipelineRun | Deploy and BDD both succeeded; 18 scenarios and 186 steps passed |
| Inspect TaskRun start/completion timestamps | BDD started after deploy completed successfully |
| Browser task security context | Ran with nonroot UID `1000600000`, using the course Selenium image |
| Add an intentional failing scenario only to the disposable source PVC | Deploy succeeded, BDD exited nonzero, and `release-bdd-failure` was Failed; the existing 18 scenarios passed |
| Combined-branch repository checks | Flake8 passed; Pylint 10.00/10; 166 unit tests passed; service coverage 98.78% |

The real multi-manifest run exposed a bug in the old JSONPath kind scan that the
mocked `oc` tests did not catch. A Go-template now handles individual resources
and Lists without the reused JSONPath range-state error. The corrected script
applied the nested Postgres manifests and application manifests successfully.

The local test used the actual course `oc` binary in an adapter Task exposing
the Red Hat `openshift-client` interface (`SCRIPT`, `manifest_dir`) through the
cluster resolver. It did **not** use an OpenShift-installed catalog Task or Route.
This verifies actual Kubernetes apply/rollout and Tekton status propagation;
it does not verify OpenShift SCCs, registry permissions, Route networking, or
the target cluster's installed Task version.

To repeat on the team's configured OpenShift project, follow [RELEASE.md](RELEASE.md)
with a matching source PVC and a genuinely built/pushed digest, then inspect:

```sh
oc get pipelinerun RUN_NAME -o jsonpath='{.status.conditions}'
oc get taskrun -l tekton.dev/pipelineRun=RUN_NAME
oc get deployment shopcarts -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Check that the actual image is the requested `repository@sha256:...`, rather than
accepting a green rollout alone. Repeat the mismatch case only in a dedicated
test environment. Final automatic ordering after the build remains dependent on
#66 and must be tested in the complete `cd-pipeline` before closing #100.
