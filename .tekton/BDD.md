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

## Integration status

The pipeline skeleton in #99 currently contains only `init`. Deploy (#100) relies
on the OpenShift manifests/Route (#65) and build task (#66). This change therefore
does not insert a reference to a missing `deploy` task into the active pipeline.
The BDD Task can be reviewed and tested independently; complete pipeline execution
remains blocked on those dependencies.

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
