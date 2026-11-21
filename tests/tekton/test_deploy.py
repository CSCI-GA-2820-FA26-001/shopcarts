"""Exercise deploy.sh at the oc boundary without accessing a cluster."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / ".tekton/scripts/deploy.sh"
DIGEST = "sha256:" + "a" * 64
MOCK_OC = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with open(os.environ["OC_LOG"], "a", encoding="utf-8") as output:
    output.write(json.dumps(args) + "\n")
if args[0] == "create":
    if args[-1] == "jsonpath={.metadata.name}":
        print("shopcarts", end="")
    elif args[-1] == "jsonpath={.kind}":
        print("Ingress", end="")
    else:
        print(os.environ.get("MOCK_KINDS", "List\nDeployment\nService\nStatefulSet\nRoute"))
elif args[:2] == ["set", "image"]:
    if os.environ.get("FAIL_RENDER"):
        sys.exit(9)
    image = next(arg for arg in args if arg.startswith("shopcarts=")).split("=", 1)[1]
    print("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: shopcarts\nspec:\n  template:"
          "\n    spec:\n      containers:\n        - name: shopcarts\n          image: " + image)
elif args[0] == "apply":
    root = Path(args[args.index("-f") + 1])
    Path(os.environ["APPLIED_MANIFEST"]).write_text((root / "deployment.yaml").read_text())
    Path(os.environ["APPLIED_FILES"]).write_text("\n".join(str(p.relative_to(root)) for p in root.rglob("*.yaml")))
    if os.environ.get("FAIL_APPLY"):
        sys.exit(7)
elif args[0] == "rollout":
    if os.environ.get("FAIL_ROLLOUT"):
        sys.exit(8)
else:
    sys.exit("Unexpected oc invocation: " + repr(args))
'''


class DeployScriptTests(unittest.TestCase):
    """Validate digest selection, no early apply, and task failure propagation."""

    def setUp(self):
        """Create disposable manifests and an oc test double."""
        # Keep the fixture alive through the test; addCleanup closes it afterward.
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "bin").mkdir()
        mock = self.root / "bin/oc"
        mock.write_text(MOCK_OC)
        mock.chmod(0o755)
        manifests = self.root / "k8s"
        (manifests / "postgres").mkdir(parents=True)
        (manifests / "deployment.yaml").write_text("kind: Deployment\nmetadata:\n  name: shopcarts\n")
        (manifests / "service.yaml").write_text("kind: Service\n")
        (manifests / "postgres/statefulset.yaml").write_text("kind: StatefulSet\n")
        (manifests / "ingress.yaml").write_text("kind: Ingress\n")
        (manifests / "route.yaml").write_text("kind: Route\n")
        self.env = dict(os.environ, PATH=f"{self.root / 'bin'}:{os.environ['PATH']}",
                        OC_LOG=str(self.root / "oc.log"),
                        APPLIED_MANIFEST=str(self.root / "applied.yaml"),
                        APPLIED_FILES=str(self.root / "applied-files"))

    def run_deploy(self, app="shopcarts", image="registry.example:5000/team/shopcarts:latest", digest=DIGEST, **env):
        """Run the real script with a disposable oc boundary."""
        return subprocess.run(["sh", str(SCRIPT), app, image, digest], cwd=self.root,
                              env=dict(self.env, **env), capture_output=True, text=True, check=False)

    def commands(self):
        """Return the attempted oc invocations in order."""
        log = self.root / "oc.log"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_applies_the_built_digest_before_waiting_for_ready(self):
        """It should apply the built image digest and wait for readiness."""
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        applied = (self.root / "applied.yaml").read_text()
        self.assertIn(f"registry.example:5000/team/shopcarts@{DIGEST}", applied)
        self.assertNotIn(":latest", applied)
        self.assertNotIn("cluster-registry", applied)
        files = (self.root / "applied-files").read_text().splitlines()
        self.assertIn("postgres/statefulset.yaml", files)
        self.assertIn("route.yaml", files)
        self.assertNotIn("ingress.yaml", files)
        self.assertEqual(self.commands()[-1], ["rollout", "status", "deployment/shopcarts", "--timeout=300s"])
        self.assertIn("--local", next(c for c in self.commands() if c[:2] == ["set", "image"]))

    def test_rejects_invalid_values_before_any_oc_command(self):
        """It should reject malformed arguments before invoking oc."""
        for values in ({"app": "bad;name"}, {"image": "bad$(command)"},
                       {"digest": "sha256:not-a-digest"}, {"app": "good\nbad"}):
            with self.subTest(values=values):
                self.assertNotEqual(self.run_deploy(**values).returncode, 0)
                self.assertEqual(self.commands(), [])

    def test_rejects_manifests_that_would_change_secrets_or_permissions(self):
        """It should keep credentials and access grants outside the deployment."""
        for kind in ("Secret", "RoleBinding", "ClusterRoleBinding"):
            with self.subTest(kind=kind):
                result = self.run_deploy(MOCK_KINDS=f"List\nDeployment\n{kind}")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(c[0] == "apply" for c in self.commands()))

    def test_mismatched_deployment_name_prevents_apply(self):
        """It should reject a different Deployment name before applying resources."""
        result = self.run_deploy(app="other-app")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[0] == "apply" for c in self.commands()))

    def test_render_failure_prevents_apply(self):
        """It should stop before apply when local image rendering fails."""
        self.assertEqual(self.run_deploy(FAIL_RENDER="1").returncode, 9)
        self.assertFalse(any(c[0] == "apply" for c in self.commands()))

    def test_apply_failure_prevents_rollout_wait(self):
        """It should propagate apply failure without claiming rollout readiness."""
        self.assertEqual(self.run_deploy(FAIL_APPLY="1").returncode, 7)
        self.assertFalse(any(c[0] == "rollout" for c in self.commands()))

    def test_rollout_failure_fails_the_task(self):
        """It should fail when the Deployment never becomes Ready."""
        self.assertEqual(self.run_deploy(FAIL_ROLLOUT="1").returncode, 8)


if __name__ == "__main__":
    unittest.main()
