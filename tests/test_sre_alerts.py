"""Alert decisions: which Alertmanager alerts Hermes asks about, and when again."""
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sre_alerts', Path(__file__).resolve().parents[1] / 'cluster/apps/hermes/sre/sre_alerts.py')
sre = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sre)

START = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def alert(name='KubePodCrashLooping', status='firing', **labels):
    labels = {'alertname': name, 'namespace': 'games', 'container': 'bedrock', 'pod': 'bedrock-0', **labels}
    return {'status': status, 'labels': labels, 'annotations': {'summary': 's'}, 'startsAt': '2026-11-10T11:50:00Z'}


class AlertDecisionsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {'SRE_ALERTS_STATE': str(Path(directory.name) / 'decisions.json')})
        env.start()
        self.addCleanup(env.stop)
        self.at(START)

    def at(self, moment):
        clock = patch.object(sre, 'now', return_value=moment)
        clock.start()
        self.addCleanup(clock.stop)

    def send(self, *alerts):
        out = io.StringIO()
        with patch('sys.stdout', out):
            sre.filter_payload({'alerts': list(alerts)})
        return json.loads(out.getvalue()) if out.getvalue() else None

    def decide(self, key, action, hours=24):
        out = io.StringIO()
        with patch('sys.stdout', out):
            sre.decide(key, action, hours)
        return out.getvalue()

    def test_new_alert_is_asked_once_with_stable_triage_request(self):
        first = self.send(alert(), alert(pod='bedrock-1'))
        self.assertEqual(first['count'], 1, 'two pods of one container are one question')
        item = first['alerts'][0]
        self.assertEqual(item['key'], 'KubePodCrashLooping/games/bedrock')
        self.assertEqual(item['triage']['workflow'], 'triage')
        self.assertRegex(item['triage']['requestId'], r'^triage-[0-9a-f]{12}$')
        self.assertEqual(item['triage']['expiresAt'], '2026-11-10T12:50:00Z')
        self.assertIsNone(self.send(alert()), 'a repeat while pending is not asked again')

    def test_unanswered_question_is_asked_again_after_a_day(self):
        self.send(alert())
        self.at(START + timedelta(hours=24))
        self.assertEqual(self.send(alert())['count'], 1)

    def test_ignore_survives_resolution(self):
        self.send(alert())
        self.decide('KubePodCrashLooping/games/bedrock', 'ignore')
        self.send(alert(status='resolved'))
        self.assertIsNone(self.send(alert()))
        self.decide('KubePodCrashLooping/games/bedrock', 'clear')
        self.assertEqual(self.send(alert())['count'], 1)

    def test_later_asks_again_only_after_its_time(self):
        self.send(alert())
        self.assertIn('2026-11-10T14:00:00Z', self.decide('KubePodCrashLooping/games/bedrock', 'later', hours=2))
        self.at(START + timedelta(hours=1))
        self.assertIsNone(self.send(alert()))
        self.at(START + timedelta(hours=2))
        self.assertEqual(self.send(alert())['count'], 1)

    def test_fix_prints_submit_fields_and_resolution_clears_it(self):
        self.send(alert())
        fields = json.loads(self.decide('KubePodCrashLooping/games/bedrock', 'fix'))
        self.assertEqual(fields['workflow'], 'fix')
        self.assertRegex(fields['requestId'], r'^fix-[0-9a-f]{12}$')
        self.assertEqual(fields, json.loads(self.decide('KubePodCrashLooping/games/bedrock', 'fix')), 'retries reuse the request')
        self.assertIsNone(self.send(alert()), 'no new question while a fix is in progress')
        self.send(alert(status='resolved'))
        self.assertEqual(self.send(alert())['count'], 1, 'a recurrence after resolution is new')

    def test_only_resolved_alerts_produce_no_payload(self):
        self.assertIsNone(self.send(alert(status='resolved')))

    def test_root_run_hands_files_back_to_the_directory_owner(self):
        directory = Path(os.environ['SRE_ALERTS_STATE']).parent
        directory.mkdir(parents=True, exist_ok=True)
        owner = directory.stat()
        changed = []
        with patch.object(sre.os, 'geteuid', return_value=0), patch.object(sre.os, 'getegid', return_value=0), \
                patch.object(sre.os, 'chown', side_effect=lambda path, uid, gid: changed.append((Path(path).suffix, uid, gid))):
            self.decide('A/b/c', 'ignore')
        self.assertEqual(sorted(changed), [('', owner.st_uid, owner.st_gid), ('.lock', owner.st_uid, owner.st_gid)])

    def test_key_falls_back_when_no_object_label(self):
        self.assertEqual(sre.alert_key({'alertname': 'TargetDown', 'namespace': 'monitoring'}), 'TargetDown/monitoring/-')


if __name__ == '__main__':
    unittest.main()
