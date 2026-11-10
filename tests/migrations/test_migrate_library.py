import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("consumer_migrations", ROOT / ".github/scripts/migrate-library.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ConsumerMigrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.consumer = self.root / "consumer"
        self.chart = self.consumer / "function"
        self.templates = self.chart / "templates"
        self.templates.mkdir(parents=True)
        self.template = self.templates / "example.yaml"
        self.template.write_text('{{ include "hmcts.a.v1.tpl" . }}\n')
        self.write_chart("1.0.0")
        self.init(self.consumer)
        self.commit(self.consumer)
        self.base = MODULE.command("git", "rev-parse", "HEAD", cwd=self.consumer).strip()
        self.library = self.root / "library"
        (self.library / "library/templates/v2").mkdir(parents=True)
        self.init(self.library)
        tooling = Path(os.environ.get("LIBRARY_TOOLING", ROOT.parent / "chart-library"))
        spec = importlib.util.spec_from_file_location(
            "shared_migrations", tooling / "scripts/template_migrations.py")
        self.engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.engine)
        (self.library / "scripts").mkdir()
        (self.library / "scripts/template_migrations.py").write_bytes(
            (tooling / "scripts/template_migrations.py").read_bytes())
        self.release("1.0.0", "hmcts.a.v1.tpl", None)
        self.write_chart("1.2.0")

    def init(self, root):
        for args in (("init", "-q"), ("config", "user.name", "Migration tests"),
                     ("config", "user.email", "test@example.invalid")):
            MODULE.command("git", *args, cwd=root)

    def commit(self, root):
        MODULE.command("git", "add", ".", cwd=root)
        MODULE.command("git", "commit", "--allow-empty", "-qm", "fixture", cwd=root)

    def write_chart(self, version):
        (self.chart / "Chart.yaml").write_text(
            "apiVersion: v2\nname: function\nversion: 0.1.0\ndependencies:\n"
            f"  - name: library\n    version: {version}\n"
            "    repository: oci://example.invalid/helm\n")

    def release(self, version, helper, entries):
        (self.library / "library/templates/v2/_a.tpl").write_text(
            '{{ define "' + helper + '" }}ok{{ end }}\n')
        if entries is not None:
            (self.library / self.engine.DECLARATIONS).write_text(json.dumps({"migrations": entries}))
        self.commit(self.library)
        MODULE.command("git", "tag", version, cwd=self.library)

    def change(self, previous, target):
        return {"from": f"hmcts.a.v{previous}.tpl", "to": f"hmcts.a.v{target}.tpl",
                "sourceFile": "library/templates/v2/_a.tpl"}

    def prepare_releases(self):
        self.release("1.1.0", "hmcts.a.v2.tpl", [self.change(1, 2)])
        self.release("1.2.0", "hmcts.a.v3.tpl", [self.change(1, 2), self.change(2, 3)])

    def test_skipped_releases_exact_replacements_and_repeat_run(self):
        self.prepare_releases()
        self.template.write_text(
            '{{ include "hmcts.a.v1.tpl" . }} {{ template `hmcts.a.v1.tpl` . }}\n'
            '{{ include "hmcts.a.v10.tpl" . }} {{/* include "hmcts.a.v1.tpl" . */}}\n')
        first = MODULE.migrate(self.consumer, self.library, self.base)
        self.assertEqual(first["rewrites"], {"1.2.0": 2})
        updated = self.template.read_text()
        self.assertIn('include "hmcts.a.v3.tpl"', updated)
        self.assertIn('template "hmcts.a.v3.tpl"', updated)
        self.assertIn('include "hmcts.a.v10.tpl"', updated)
        self.assertIn('/* include "hmcts.a.v1.tpl"', updated)
        self.assertEqual(MODULE.migrate(self.consumer, self.library, self.base)["rewrites"], {})
        self.assertEqual(self.template.read_text(), updated)

    def test_no_dependency_change_needs_no_history(self):
        self.write_chart("1.0.0")
        self.assertEqual(MODULE.migrate(self.consumer, self.library, self.base)["rewrites"], {})

    def test_no_matching_references(self):
        self.prepare_releases()
        self.template.write_text('{{ include "function.local" . }}')
        self.assertEqual(MODULE.migrate(self.consumer, self.library, self.base)["rewrites"], {})

    def test_missing_history_fails(self):
        self.release("1.2.0", "hmcts.a.v1.tpl", None)
        with self.assertRaisesRegex(ValueError, "predates"):
            MODULE.migrate(self.consumer, self.library, self.base)

    def test_missing_mapping_fails_without_writes(self):
        self.release("1.2.0", "hmcts.a.v3.tpl", [])
        before = self.template.read_bytes()
        with self.assertRaisesRegex(ValueError, "lack migrations"):
            MODULE.migrate(self.consumer, self.library, self.base)
        self.assertEqual(self.template.read_bytes(), before)

    def test_indirect_reference_fails_without_writes(self):
        self.prepare_releases()
        self.template.write_text(
            '{{ include "hmcts.a.v1.tpl" . }}{{ $helper := "hmcts.a.v1.tpl" }}{{ include $helper . }}')
        before = self.template.read_bytes()
        with self.assertRaisesRegex(ValueError, "manual migration"):
            MODULE.migrate(self.consumer, self.library, self.base)
        self.assertEqual(self.template.read_bytes(), before)

    def test_missing_release_tag_fails(self):
        with self.assertRaises(subprocess.CalledProcessError):
            MODULE.migrate(self.consumer, self.library, self.base)

    def test_range_rejected(self):
        self.write_chart('">=1.0.0"')
        with self.assertRaisesRegex(ValueError, "exact stable version"):
            MODULE.migrate(self.consumer, self.library, self.base)

    def test_downgrade_rejected(self):
        self.write_chart("0.9.0")
        with self.assertRaisesRegex(ValueError, "downgrades"):
            MODULE.migrate(self.consumer, self.library, self.base)

    def test_cli_reports_failure(self):
        result = subprocess.run(
            [sys.executable, "-S", str(ROOT / ".github/scripts/migrate-library.py"),
             "--consumer", str(self.consumer), "--library", str(self.library), "--base", self.base],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Consumer migration failed:", result.stderr)

    def test_cli_success_and_edit_scope(self):
        self.prepare_releases()
        chart_before = (self.chart / "Chart.yaml").read_bytes()
        result = subprocess.run(
            [sys.executable, "-S", str(ROOT / ".github/scripts/migrate-library.py"),
             "--consumer", str(self.consumer), "--library", str(self.library), "--base", self.base],
            check=True, text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout)["rewrites"], {"1.2.0": 1})
        self.assertEqual((self.chart / "Chart.yaml").read_bytes(), chart_before)
        changed = MODULE.command("git", "diff", "--name-only", cwd=self.consumer).splitlines()
        self.assertEqual(set(changed), {"function/Chart.yaml", "function/templates/example.yaml"})

    def test_symlinked_template_rejected(self):
        self.prepare_releases()
        external = self.root / "external.tpl"
        external.write_text('{{ include "hmcts.a.v1.tpl" . }}')
        (self.templates / "external.yaml").symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            MODULE.migrate(self.consumer, self.library, self.base)
        self.assertIn("hmcts.a.v1.tpl", external.read_text())


if __name__ == "__main__":
    unittest.main()
