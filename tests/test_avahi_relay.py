"""Exercise interface ownership and fail-closed selection without host mutations."""
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('relay', Path(__file__).resolve().parents[1] / 'cluster/apps/networking/avahi-daemon/reconcile.py')
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def pod(name='music', **extra):
    return {'metadata': {'name': name}, 'spec': {'nodeName': 'vecna', **extra},
            'status': {'phase': 'Running', 'podIP': '10.42.228.209'}}


class RelayTest(unittest.TestCase):
    def test_only_one_local_non_host_pod(self):
        target = pod()
        self.assertEqual(relay.select_target([pod(hostNetwork=True), pod(nodeName='other'), target], 'vecna'), target)
        target['metadata']['deletionTimestamp'] = 'now'
        self.assertIsNone(relay.select_target([target], 'vecna'))
        with self.assertRaisesRegex(RuntimeError, 'More than one'):
            relay.select_target([pod(), pod('duplicate')], 'vecna')

    def test_restart_retains_ownership_then_cleans_only_its_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(relay, 'CONFIG', base / 'config'), patch.object(relay, 'STATE', base / 'owned.json'), \
                 patch.object(relay, 'ip') as ip, patch.object(relay, 'addresses') as addresses, \
                 patch.object(relay, 'interface_index', return_value=123):
                ip.return_value = '10.42.228.209 dev cali123 scope link'
                addresses.return_value = []
                relay.configure(pod(), 'enp5s0', ['_spotify-connect._tcp.local'])
                ip.assert_any_call('address', 'add', '169.254.1.1/32', 'dev', 'cali123')
                self.assertIn('allow-interfaces=enp5s0,cali123\n', relay.CONFIG.read_text())
                ip.reset_mock()
                addresses.return_value = ['169.254.1.1/32']
                relay.configure(pod(), 'enp5s0', ['_spotify-connect._tcp.local'])
                self.assertFalse(any(c.args[:2] == ('address', 'add') for c in ip.call_args_list))
                ip.return_value = '10.42.228.209 scope link'
                relay.cleanup()
                ip.assert_any_call('route', 'replace', '10.42.228.209/32', 'dev', 'cali123', 'scope', 'link')
                ip.assert_any_call('address', 'del', '169.254.1.1/32', 'dev', 'cali123')
                self.assertFalse(relay.CONFIG.exists())
                self.assertFalse(relay.STATE.exists())

    def test_cleanup_recovers_interrupted_route_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(relay, 'CONFIG', base / 'config'), patch.object(relay, 'STATE', base / 'owned.json'), \
                 patch.object(relay, 'interface_index', return_value=123), \
                 patch.object(relay, 'addresses', return_value=[]), patch.object(relay, 'ip') as ip:
                relay.STATE.write_text(json.dumps({'owned': True, 'interface': 'cali123', 'ifindex': 123,
                                                 'address': '10.42.228.209', 'restore_route': True}))
                relay.cleanup()
                ip.assert_called_once_with('route', 'replace', '10.42.228.209/32', 'dev', 'cali123', 'scope', 'link')
                self.assertFalse(relay.STATE.exists())

    def test_reused_interface_name_is_not_owned(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(relay, 'CONFIG', base / 'config'), patch.object(relay, 'STATE', base / 'owned.json'), \
                 patch.object(relay, 'interface_index', return_value=456), patch.object(relay, 'ip') as ip:
                relay.STATE.write_text(json.dumps({'owned': True, 'interface': 'cali123', 'ifindex': 123}))
                relay.cleanup()
                ip.assert_not_called()
                self.assertFalse(relay.STATE.exists())

    def test_does_not_adopt_unowned_alias(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(relay, 'STATE', Path(directory) / 'owned.json'), \
             patch.object(relay, 'ip', return_value='dev cali123') as ip, \
             patch.object(relay, 'addresses', return_value=['169.254.1.1/32']):
            with self.assertRaisesRegex(RuntimeError, 'unowned'):
                relay.configure(pod(), 'enp5s0', ['_spotify-connect._tcp.local'])
            self.assertEqual(ip.call_count, 1)


if __name__ == '__main__':
    unittest.main()
