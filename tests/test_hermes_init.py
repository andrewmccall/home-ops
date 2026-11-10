"""Hermes init: Git seeds Hermes's files once and pins only the managed settings."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'cluster/apps/hermes'
spec = importlib.util.spec_from_file_location('hermes_init', ROOT / 'init.py')
init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init)


class HermesInitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in ('data', 'seed', 'managed', 'sre', 'trust', 'ca'):
            (self.root / name).mkdir()
        (self.root / 'seed/config.yaml').write_text((ROOT / 'seed/config.yaml').read_text())
        (self.root / 'seed/SOUL.md').write_text('You are Ada.\n')
        (self.root / 'managed/config.yaml').write_text((ROOT / 'managed/config.yaml').read_text())
        for name in ('sre_alerts.py', 'SKILL.md'):
            (self.root / 'sre' / name).write_text(name)
        (self.root / 'trust/sproozi-tasks-ca.crt').write_text('CA\n')
        (self.root / 'roots.pem').write_text('ROOTS\n')

    def run_init(self):
        init.main(data=self.root / 'data', seed=self.root / 'seed', managed=self.root / 'managed/config.yaml',
                  sre=self.root / 'sre', trust=self.root / 'trust', bundle=self.root / 'ca/ca-bundle.pem',
                  system_roots=self.root / 'roots.pem', chown=False)

    def test_seeds_once_then_keeps_hermes_edits(self):
        self.run_init()
        self.assertIn('claude-sonnet-5-5', (self.root / 'data/config.yaml').read_text())
        self.assertEqual((self.root / 'data/SOUL.md').read_text(), 'You are Ada.\n')
        (self.root / 'data/SOUL.md').write_text('You are Ada, and you like tea.\n')
        (self.root / 'data/config.yaml').write_text('# mine\nmodel:\n  provider: anthropic\n  default: claude-opus-5-5\n')
        self.run_init()
        self.assertEqual((self.root / 'data/SOUL.md').read_text(), 'You are Ada, and you like tea.\n')
        self.assertEqual((self.root / 'data/config.yaml').read_text(),
                         '# mine\nmodel:\n  provider: anthropic\n  default: claude-opus-5-5\n')

    def test_removes_pinned_leaves_and_keeps_hermes_siblings(self):
        (self.root / 'data/config.yaml').write_text(
            'model:\n  default: claude-sonnet-5-5\n'
            'platform_toolsets:\n  webhook: [hermes-webhook, home_assistant]\n  cli: [hermes-cli]\n'
            'mcp_servers:\n  home_assistant:\n    url: http://elsewhere\n  notes:\n    url: http://notes\n'
            'platforms:\n  webhook:\n    extra:\n      port: 9999\n')
        self.run_init()
        text = (self.root / 'data/config.yaml').read_text()
        for gone in ('home_assistant', 'elsewhere', '9999', 'webhook'):
            self.assertNotIn(gone, text)
        for kept in ('cli: [hermes-cli]', 'notes:', 'http://notes', 'claude-sonnet-5-5'):
            self.assertIn(kept, text)
        self.assertNotIn('platforms', text, 'parents emptied by pruning are removed')

    def test_installs_bundle_and_alert_files(self):
        self.run_init()
        self.assertEqual((self.root / 'ca/ca-bundle.pem').read_text(), 'ROOTS\nCA\n')
        self.assertEqual((self.root / 'data/scripts/sre_alerts.py').read_text(), 'sre_alerts.py')
        self.assertEqual((self.root / 'data/skills/devops/sre-alerts/SKILL.md').read_text(), 'SKILL.md')


if __name__ == '__main__':
    unittest.main()
