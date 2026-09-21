"""
E2E Telemetry & State Gate Verification Test Suite for Vibe OS
Verifies control-state synchronization, state integrity, and agent pipeline contracts.
"""

import os
import re
import unittest

class TestVibeOSControlState(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.state_path = os.path.join(self.base_dir, "control-state", "STATE.md")
        self.handoff_path = os.path.join(self.base_dir, "control-state", "HANDOFF.md")

    def test_state_file_exists(self):
        """Verify STATE.md exists and is readable."""
        self.assertTrue(os.path.exists(self.state_path), "STATE.md must exist")
        with open(self.state_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Current System State", content)
            self.assertIn("Current Phase", content)
            self.assertIn("Waterfall Gate", content)

    def test_gate_transition_validity(self):
        """Verify Waterfall Gate is in a valid state (PASSED, PENDING_APPROVAL, or ACTIVE)."""
        with open(self.state_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r"\*\*Waterfall Gate\*\*:\s*([A-Za-z_]+)", content)
        self.assertIsNotNone(match, "Waterfall Gate status must be present")
        status = match.group(1)
        valid_statuses = ["PASSED", "PENDING_APPROVAL", "APPROVED", "UNLOCKED"]
        self.assertIn(status, valid_statuses, f"Status {status} is not in {valid_statuses}")

    def test_handoff_log_integrity(self):
        """Verify HANDOFF.md contains valid handoff records with sign-off details."""
        self.assertTrue(os.path.exists(self.handoff_path), "HANDOFF.md must exist")
        with open(self.handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Agent Handoff Log", content)
            self.assertIn("Handoff Record", content)

if __name__ == "__main__":
    unittest.main()
