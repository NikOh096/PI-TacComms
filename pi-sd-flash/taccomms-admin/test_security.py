import json
import tempfile
import unittest
from pathlib import Path
from security import SecurityStore, SecurityError
from gestures import TapGesture

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.now=1000; self.events=[]
        self.store=SecurityStore(self.temp.name,clock=lambda:self.now,audit=lambda event,**kw:self.events.append((event,kw)))
        self.admin='284691'; self.recovery='739205'
    def enroll(self):
        self.store.enroll(self.admin,self.admin,self.recovery,self.recovery)
    def test_first_use_and_hash_only(self):
        self.assertFalse(self.store.public_state()['enrolled'])
        with self.assertRaises(SecurityError): self.store.emergency()
        with self.assertRaises(SecurityError): self.store.enroll(self.admin,self.admin,self.admin,self.admin)
        with self.assertRaises(SecurityError): self.store.enroll('123','123',self.recovery,self.recovery)
        self.enroll()
        data=(Path(self.temp.name)/'pins.json').read_text()
        self.assertNotIn(self.admin,data); self.assertNotIn(self.recovery,data)
        self.assertNotEqual(self.store.pins['admin']['salt'],self.store.pins['recovery']['salt'])
        with self.assertRaises(SecurityError): self.enroll()
    def test_emergency_survives_restart_and_requires_separate_pin(self):
        self.enroll(); token=self.store.login(self.admin,1000); self.store.emergency()
        with self.assertRaises(SecurityError): self.store.authorize(token,1000)
        restarted=SecurityStore(self.temp.name,clock=lambda:self.now)
        self.assertTrue(restarted.public_state()['emergency'])
        with self.assertRaises(SecurityError): restarted.login(self.admin,1000)
        with self.assertRaises(SecurityError): restarted.recover(self.admin)
        restarted.recover(self.recovery)
        self.assertFalse(restarted.public_state()['emergency'])
        with self.assertRaises(SecurityError): restarted.authorize(token,1000)
        restarted.authorize(restarted.login(self.admin,1000),1000)
    def test_rate_limit_persists(self):
        self.enroll()
        for _ in range(5):
            with self.assertRaises(SecurityError): self.store.login('999999',1000)
        self.assertGreater(self.store.public_state()['retry_after']['admin'],0)
        restarted=SecurityStore(self.temp.name,clock=lambda:self.now)
        with self.assertRaises(SecurityError): restarted.login(self.admin,1000)
        self.now+=31; restarted.login(self.admin,1000)
    def test_sessions_expire_and_are_uid_bound(self):
        self.enroll(); token=self.store.login(self.admin,1000)
        with self.assertRaises(SecurityError): self.store.authorize(token,1001)
        token=self.store.login(self.admin,1000)
        self.now+=50; self.store.authorize(token,1000)
        self.now+=11
        with self.assertRaises(SecurityError): self.store.authorize(token,1000)
        token=self.store.login(self.admin,1000)
        self.now+=50; self.store.authorize(token,1000,touch=True)
        self.now+=50; self.store.authorize(token,1000)
    def test_pin_changes_invalidate_sessions(self):
        self.enroll(); token=self.store.login(self.admin,1000)
        with self.assertRaises(SecurityError): self.store.change_pin('recovery','456782','456782',self.admin)
        self.store.change_pin('admin','456782','456782')
        with self.assertRaises(SecurityError): self.store.authorize(token,1000)
        self.store.login('456782',1000)
        self.assertNotIn('456782',json.dumps(self.events))

class Gestures(unittest.TestCase):
    def test_five_complete_taps_inside_half_second(self):
        g=TapGesture()
        actions=[g.tap(i*.1,i*.1+.05) for i in range(5)]
        self.assertEqual(actions,[None,None,None,None,'emergency'])
        self.assertIsNone(g.flush(1))
    def test_exact_boundary(self):
        g=TapGesture()
        for i in range(4): self.assertIsNone(g.tap(i*.1,i*.1+.04))
        self.assertEqual(g.tap(.4,.5),'emergency')
    def test_slow_taps_and_holds_do_not_emergency_lock(self):
        g=TapGesture()
        for i in range(5): self.assertNotEqual(g.tap(i*.12,i*.12+.03),'emergency')
        self.assertIsNone(g.tap(2,3))
    def test_double_tap_remains_distinct(self):
        g=TapGesture(); g.tap(0,.04); g.tap(.18,.22)
        self.assertIsNone(g.flush(.49)); self.assertEqual(g.flush(.501),'double')
    def test_four_taps_dont_enter_admin(self):
        g=TapGesture()
        for i in range(4): g.tap(i*.1,i*.1+.05)
        self.assertIsNone(g.flush(.6))

if __name__=='__main__': unittest.main()
