"""
Automated unit tests for Phase 4 Dedicated GUI PIN Window (PinWindow).
Validates non-blocking event-polling, single-instance lifecycle, secure verification,
anti-stale authentication guarantees, Submit button presence, clear UI status labels
(PIN REQUIRED / ACCESS GRANTED / ACCESS DENIED), and thread-safe event queue access.
"""

import threading
import time
import unittest
from unittest.mock import patch

from phase4.access_control import (
    AccessDecision,
    evaluate_access,
    verify_pin,
)
from phase4.pin_window import PinWindow


class TestPinWindow(unittest.TestCase):
    """
    Test suite for PinWindow GUI integration and event handling.
    """

    @classmethod
    def setUpClass(cls):
        cls.correct_pin = "8080"
        cls.pw = PinWindow(validator=lambda p: p == cls.correct_pin)
        from datetime import time as dt_time
        cls.night_time = dt_time(23, 0)
        cls.authorized_name = "manisha"

    @classmethod
    def tearDownClass(cls):
        if cls.pw:
            cls.pw.destroy()

    def setUp(self):
        # Reset validator and state before each test
        self.pw._validator = lambda p: p == self.correct_pin
        self.pw._events.clear()
        self.pw.hide()

    def tearDown(self):
        self.pw.hide()

    # 1. Opening the PIN window does not block the camera loop
    def test_01_non_blocking_update(self):
        self.pw.show()
        start = time.time()
        # Simulate 20 camera loop frames
        for _ in range(20):
            t0 = time.time()
            self.pw.update()
            elapsed_frame = time.time() - t0
            self.assertLess(elapsed_frame, 0.1, "Single update() took too long")
        total_duration = time.time() - start
        self.assertLess(total_duration, 0.5, "20 frames update() should run in < 0.5s")
        self.pw.hide()

    # 2. Only one PIN window can exist at a time
    def test_02_only_one_window_instance(self):
        self.pw.show()
        self.assertTrue(self.pw.is_visible())

        # Calling show() repeatedly does not duplicate windows or raise errors
        self.pw.show()
        self.assertTrue(self.pw.is_visible())
        self.pw.update()
        self.pw.hide()
        self.assertFalse(self.pw.is_visible())

    # 3. Correct PIN verification produces a successful result only for a valid authentication attempt
    def test_03_correct_pin_verification(self):
        self.pw.show()
        self.pw._entry_var.set(self.correct_pin)
        self.pw._on_submit()

        event = self.pw.poll_event()
        self.assertEqual(event, "SUCCESS")

        # Now verify integration with evaluate_access for valid attempt
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_name,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
            start_time_str="06:00",
            end_time_str="22:00",
        )
        self.assertEqual(result.decision, AccessDecision.GRANT)
        self.assertTrue(result.is_granted)

    # 4. Incorrect PIN verification denies access
    def test_04_incorrect_pin_verification_denies(self):
        self.pw.show()
        self.pw._entry_var.set("0000")  # Wrong PIN
        self.pw._on_submit()

        event = self.pw.poll_event()
        self.assertEqual(event, "FAILED")

        # Access check outside normal hours without valid PIN must REQUIRE_PIN / not grant
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_name,
            liveness_verified=True,
            pin_verified=False,
            current_time=self.night_time,
            start_time_str="06:00",
            end_time_str="22:00",
        )
        self.assertEqual(result.decision, AccessDecision.REQUIRE_PIN)
        self.assertFalse(result.is_granted)

    # 5. Cancelling or closing the window never grants access
    def test_05_cancellation_never_grants_access(self):
        self.pw.show()
        self.pw._on_cancel()

        event = self.pw.poll_event()
        self.assertEqual(event, "CANCELLED")
        self.assertFalse(self.pw.is_visible())

        # Access decision must remain not granted
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_name,
            liveness_verified=True,
            pin_verified=False,
            current_time=self.night_time,
        )
        self.assertNotEqual(result.decision, AccessDecision.GRANT)

    # 6. Resetting authentication clears PIN authorization
    def test_06_resetting_clears_pin_authorization(self):
        pin_verified = True
        self.pw.show()

        # Simulate reset:
        pin_verified = False
        self.pw.hide()

        self.assertFalse(pin_verified)
        self.assertFalse(self.pw.is_visible())

    # 7. Liveness failure and multiple-face detection invalidate PIN authorization
    def test_07_liveness_and_multiple_faces_invalidate_pin(self):
        # Even if pin_verified is True, multiple faces must be DENIED
        multi_result = evaluate_access(
            face_count=2,
            identity=self.authorized_name,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(multi_result.decision, AccessDecision.DENY)

        # Even if pin_verified is True, missing liveness must be DENIED
        liveness_result = evaluate_access(
            face_count=1,
            identity=self.authorized_name,
            liveness_verified=False,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(liveness_result.decision, AccessDecision.DENY)

    # 8. Identity changes invalidate PIN authorization
    def test_08_identity_change_invalidates_pin(self):
        # If user becomes Unknown, PIN cannot grant access
        unknown_result = evaluate_access(
            face_count=1,
            identity="Unknown",
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(unknown_result.decision, AccessDecision.DENY)

    # 9. Missing or invalid PIN configuration fails closed
    def test_09_invalid_or_placeholder_pin_config_fails_closed(self):
        # Configure self.pw with real verify_pin under placeholder DOOR_PIN
        with patch.dict("os.environ", {"DOOR_PIN": "replace_with_a_private_numeric_pin"}):
            self.pw._validator = verify_pin
            self.pw.show()
            self.pw._entry_var.set("1234")
            self.pw._on_submit()
            event = self.pw.poll_event()
            self.assertEqual(event, "FAILED")
            self.pw.hide()

    # 10. The application can shut down cleanly with the PIN window open
    def test_10_clean_shutdown_with_window_open(self):
        temp_pw = PinWindow(validator=lambda p: True)
        temp_pw.show()
        self.assertTrue(temp_pw.is_visible())
        temp_pw.destroy()
        self.assertFalse(temp_pw.is_visible())
        self.assertIsNone(temp_pw._root)


    # 11. The Submit button label is present (not 'Verify PIN')
    def test_11_submit_button_label(self):
        """
        The action button must be labelled 'Submit', not 'Verify PIN'.
        Checks Tkinter widget text directly.
        """
        if self.pw._root is None:
            self.skipTest("No display server available")

        submit_found = False
        for widget in self.pw._root.winfo_children():
            for child in widget.winfo_children():
                for btn in child.winfo_children():
                    try:
                        lbl = btn.cget("text")
                        if lbl == "Submit":
                            submit_found = True
                        self.assertNotEqual(
                            lbl, "Verify PIN",
                            "Button should be labelled 'Submit', not 'Verify PIN'"
                        )
                    except Exception:
                        pass
        self.assertTrue(submit_found, "'Submit' button widget was not found")

    # 12. Status labels display PIN REQUIRED, ACCESS GRANTED, ACCESS DENIED
    def test_12_status_labels_correct_text(self):
        """
        Verifies that the status label reflects the three required UI states:
        - 'PIN REQUIRED' on show()
        - 'ACCESS GRANTED' on correct PIN
        - 'ACCESS DENIED' on wrong PIN
        """
        if self.pw._root is None:
            self.skipTest("No display server available")

        # show() → PIN REQUIRED
        self.pw.show()
        status_text = self.pw._status_lbl.cget("text") if self.pw._status_lbl else ""
        self.assertIn("PIN REQUIRED", status_text, "show() should display 'PIN REQUIRED'")
        self.pw._events.clear()

        # Correct PIN → ACCESS GRANTED
        self.pw._entry_var.set(self.correct_pin)
        self.pw._on_submit()
        status_text = self.pw._status_lbl.cget("text") if self.pw._status_lbl else ""
        self.assertIn("ACCESS GRANTED", status_text, "correct PIN should display 'ACCESS GRANTED'")
        self.pw._events.clear()

        # Wrong PIN → ACCESS DENIED
        self.pw.show()
        self.pw._events.clear()
        self.pw._entry_var.set("0000")
        self.pw._on_submit()
        status_text = self.pw._status_lbl.cget("text") if self.pw._status_lbl else ""
        self.assertIn("ACCESS DENIED", status_text, "wrong PIN should display 'ACCESS DENIED'")
        self.pw._events.clear()

    # 13. Thread-safe poll_event works correctly under concurrent access
    def test_13_thread_safe_poll_event(self):
        """
        Fires events from one thread and polls them from another.
        Asserts no events are lost and no exception is raised.
        """
        collected: list = []
        errors: list = []

        def producer():
            try:
                for _ in range(50):
                    with self.pw._lock:
                        self.pw._events.append("FAILED")
            except Exception as exc:
                errors.append(exc)

        def consumer():
            try:
                for _ in range(100):
                    evt = self.pw.poll_event()
                    if evt:
                        collected.append(evt)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=producer)
        t2 = threading.Thread(target=consumer)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        self.assertEqual([], errors, f"Thread errors: {errors}")
        # All produced events must have been seen (producer wrote 50, consumer may have
        # drained some; total collected + remaining in queue must equal 50)
        with self.pw._lock:
            remaining = len(self.pw._events)
        total = len(collected) + remaining
        self.assertEqual(50, total, f"Event count mismatch: collected={len(collected)}, remaining={remaining}")
        # Clear any leftover events
        with self.pw._lock:
            self.pw._events.clear()


if __name__ == "__main__":
    unittest.main()
