import sys,unittest
from pathlib import Path
from unittest.mock import patch
import monitor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'taccomms-admin'))
import client

class DiagnosticsTests(unittest.TestCase):
    def test_unknown_power_is_not_healthy(self):
        self.assertEqual(monitor.power_flags('unavailable')['flags'],{})
        self.assertEqual(monitor.power_flags('throttled=0x0')['flags']['undervoltage_now'],False)
    def test_power_now_vs_since_boot(self):
        flags=monitor.power_flags('throttled=0x50000')['flags']
        self.assertFalse(flags['undervoltage_now'])
        self.assertTrue(flags['undervoltage_since_boot']);self.assertTrue(flags['throttled_since_boot'])
        self.assertTrue(monitor.power_flags('throttled=0x50005')['flags']['undervoltage_now'])
    def test_boot_classification_is_cautious(self):
        self.assertIn('unavailable',monitor.boot_assessment({}, {'boot_id':'b'}))
        self.assertIn('same boot',monitor.boot_assessment({'boot_id':'b'},{'boot_id':'b'}))
        self.assertIn('cause is unconfirmed',monitor.boot_assessment({'boot_id':'a'},{'boot_id':'b'}))
        self.assertIn('orderly shutdown request',monitor.boot_assessment({'boot_id':'a','exit_reason':'system_shutdown'},{'boot_id':'b'}))
    def test_startup_waits_for_socket_without_replaying_commands(self):
        with patch.object(client,'request',side_effect=[FileNotFoundError(),ConnectionRefusedError(),{'enrolled':True,'emergency':True}]) as request, patch.object(client.time,'sleep'):
            self.assertTrue(client.wait_ready()['emergency'])
            self.assertEqual([c.args for c in request.call_args_list],[('state',)]*3)
    def test_startup_timeout_fails_closed(self):
        with patch.object(client,'request',side_effect=FileNotFoundError()),patch.object(client.time,'monotonic',side_effect=[0,31]):
            with self.assertRaises(RuntimeError):client.wait_ready()

if __name__=='__main__':unittest.main()
