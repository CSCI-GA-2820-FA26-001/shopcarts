# BDD pipeline task (#101)

`tasks.yaml` defines the custom `behave` Task using the course Selenium image.
It receives `BASE_URL` as an environment variable, installs the committed lockfile
into a temporary virtual environment, and runs the existing `features/` suite.
Installation uses `--require-hashes --no-deps` to install exactly the committed
locked package set, without resolving additional dependencies, matching Pipenv
sync's locked-install behavior. The Task does not modify or regenerate the lock.
A failed dependency installation or scenario fails the Task. The cloned source
is mounted read-only; generated dependencies and browser cache/config directories
are under `/tmp`. The Task does not require root or change `HOME`.

**Use an isolated test deployment.** The existing BDD fixtures delete shopcarts
between scenarios. `BASE_URL` must identify that deployment's HTTP/HTTPS Route,
not a shared demo or production instance.

## Run deploy followed by BDD

The executable `shopcarts-release` Pipeline runs `deploy`, then `bdd`. BDD starts
only after deployment succeeds; a failed scenario fails the PipelineRun. Follow
the [post-build release guide](RELEASE.md) for cluster prerequisites, the matching
image/source inputs, and the `tkn pipeline start` command.

Apply the Task and executable Pipeline:

```sh
oc apply -f .tekton/tasks.yaml -f .tekton/release-pipeline.yaml
```

The shared workspace must already contain the source revision used to build the
image, including `.tekton/scripts/run-bdd.sh`, the lockfile, and the feature suite.
The Pipeline's `BASE_URL` must point to that deployment's isolated test Route.

## Full CD integration

The separate `cd-pipeline` skeleton in #99 still contains only `init`. The
post-build release path does not implement the remaining clone, lint, unit-test,
and build stories. Automatic build-to-deploy-to-BDD execution requires those
upstream stages and the OpenShift deployment prerequisites (#65).

After clone, build, and deploy have been integrated:

1. Insert `.tekton/integration/bdd-task.yaml` under `spec.tasks` in
   `.tekton/pipeline.yaml`. It runs after `deploy`, references the `behave` Task,
   and maps `pipeline-workspace` to `source`.
2. Supply the isolated Route URL as the PipelineRun's `BASE_URL` parameter. The
   cloned revision must include this Task's `.tekton/scripts/run-bdd.sh`.
3. Apply the standalone Task and Pipeline manifests explicitly, for example
   `oc apply -f .tekton/tasks.yaml -f .tekton/pipeline.yaml`. Do not recursively
   apply `.tekton/`: `integration/` contains fragments, not Kubernetes resources.
4. Run the Pipeline on OpenShift. Confirm deploy completes before BDD starts,
   all scenarios pass, and a deliberately failing scenario makes the PipelineRun
   fail. Also verify execution with the cluster's assigned nonroot UID.

## Local validation

Run `python -m unittest discover -s tests/tekton -v` for runner failure-propagation
tests. These substitute Python tooling and do not prove browser/cluster behavior.

For the real suite, run the script from the repository root inside the Selenium
image, with `BASE_URL` pointing at a disposable running application and its test
database. The image supplies Python, Pipenv, Chrome, and ChromeDriver; the script
installs application/test packages from `Pipfile.lock`. Successful local execution
does not verify OpenShift Route networking or the full PipelineRun.
