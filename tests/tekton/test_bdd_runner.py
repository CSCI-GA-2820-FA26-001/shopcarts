"""Check that the BDD runner fails correctly without contacting a real cluster."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


RUNNER = Path(__file__).resolve().parents[2] / ".tekton" / "scripts" / "run-bdd.sh"


class TestBddRunner(unittest.TestCase):
    """Exercise the shell runner with substitute Python tools."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "Pipfile").write_text("[packages]\n", encoding="utf-8")
        (self.source / "Pipfile.lock").write_text("{}\n", encoding="utf-8")
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.log = self.root / "calls.jsonl"
        substitute = self.bin_dir / "python"
        substitute.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent(
                """
                import json
                import os
                from pathlib import Path
                import shutil
                import sys

                args = sys.argv[1:]
                with open(os.environ["CALLS_LOG"], "a", encoding="utf-8") as log:
                    log.write(json.dumps({"args": args, "BASE_URL": os.getenv("BASE_URL")}) + "\\n")
                if args[:2] == ["-m", "venv"]:
                    target = Path(args[2]) / "bin" / "python"
                    target.parent.mkdir(parents=True)
                    shutil.copy2(__file__, target)
                elif args == ["-m", "pipenv", "verify"]:
                    sys.exit(int(os.getenv("VERIFY_EXIT", "0")))
                elif args[:3] == ["-m", "pipenv", "requirements"]:
                    print("behave==1.3.3 --hash=sha256:test-fixture")
                elif args[:3] == ["-m", "pip", "install"]:
                    if "--require-hashes" not in args or "--no-deps" not in args:
                        sys.exit(90)
                    sys.exit(int(os.getenv("INSTALL_EXIT", "0")))
                elif args == ["-m", "behave"]:
                    sys.exit(int(os.getenv("BEHAVE_EXIT", "0")))
                else:
                    sys.exit(91)
                """
            ),
            encoding="utf-8",
        )
        substitute.chmod(0o755)

    def run_script(self, **overrides):
        """Run the actual shell script with controllable dependency exit codes."""
        env = dict(os.environ)
        env.update(
            PATH=f"{self.bin_dir}:{env['PATH']}",
            BASE_URL="https://shopcarts-test.example",
            CALLS_LOG=str(self.log),
            TMPDIR=str(self.root),
        )
        env.update(overrides)
        return subprocess.run(
            ["/bin/sh", str(RUNNER)],
            cwd=self.source,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def calls(self):
        """Read the subprocess calls produced by the substituted tooling."""
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_rejects_missing_or_invalid_base_url(self):
        """Reject an unconfigured deployment before installing dependencies."""
        for url in ("", "localhost:8080", "https://"):
            with self.subTest(url=url):
                result = self.run_script(BASE_URL=url)
                self.assertEqual(result.returncode, 2)
                self.assertIn("BASE_URL", result.stderr)
                self.assertEqual(self.calls(), [])

    def test_rejects_missing_lockfile(self):
        """Do not silently resolve new dependency versions when the lock is missing."""
        (self.source / "Pipfile.lock").unlink()
        result = self.run_script()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_stale_lock_stops_before_installation(self):
        """A failed Pipenv verification prevents installation and scenarios."""
        result = self.run_script(VERIFY_EXIT="3")
        self.assertEqual(result.returncode, 3)
        self.assertEqual([call["args"] for call in self.calls()], [["-m", "pipenv", "verify"]])

    def test_failed_install_does_not_run_behave(self):
        """Dependency failure must fail the Task rather than run stale packages."""
        result = self.run_script(INSTALL_EXIT="4")
        self.assertEqual(result.returncode, 4)
        self.assertFalse(any(call["args"] == ["-m", "behave"] for call in self.calls()))

    def test_failed_scenario_is_not_hidden(self):
        """Behave's nonzero status is returned to Tekton unchanged."""
        result = self.run_script(BEHAVE_EXIT="7")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.calls()[-1]["args"], ["-m", "behave"])

    def test_success_passes_route_and_preserves_source(self):
        """Pass the configured Route to Behave without generating repository files."""
        before = {path.name: path.read_bytes() for path in self.source.iterdir()}
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-1]["BASE_URL"], "https://shopcarts-test.example")
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.source.iterdir()})


if __name__ == "__main__":
    unittest.main()
