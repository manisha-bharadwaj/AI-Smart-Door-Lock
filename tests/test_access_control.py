"""
Automated unit tests for Phase 4: Adaptive Security Access Control.
Validates all mandatory access rules, time-window logic, and secure PIN handling.
"""

import unittest
from datetime import time
from unittest.mock import patch

from phase4.access_control import (
    AccessDecision,
    AccessResult,
    evaluate_access,
    is_valid_pin_configuration,
    is_within_normal_hours,
    parse_time_str,
    verify_pin,
)


class TestAccessControl(unittest.TestCase):
    """
    Test suite for Phase 4 adaptive security access-control logic.
    """

    def setUp(self):
        # Default test parameters
        self.day_time = time(14, 0)      # 14:00 (inside 06:00 - 22:00)
        self.night_time = time(23, 30)   # 23:30 (outside 06:00 - 22:00)
        self.morning_start = "06:00"
        self.evening_end = "22:00"
        self.authorized_user = "manisha"
        self.test_pin = "8492"

    # 1. Unknown or unauthorized identity is denied
    def test_01_unknown_or_unauthorized_identity_denied(self):
        result_unknown = evaluate_access(
            face_count=1,
            identity="Unknown",
            liveness_verified=True,
            current_time=self.day_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result_unknown.decision, AccessDecision.DENY)
        self.assertIn("Unauthorized", result_unknown.reason)

        result_unregistered = evaluate_access(
            face_count=1,
            identity="Intruder",
            liveness_verified=True,
            authorized_names=["manisha", "alice"],
            current_time=self.day_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result_unregistered.decision, AccessDecision.DENY)
        self.assertIn("Unauthorized", result_unregistered.reason)

    # 2. Zero faces are denied
    def test_02_zero_faces_denied(self):
        result = evaluate_access(
            face_count=0,
            identity=self.authorized_user,
            liveness_verified=True,
            current_time=self.day_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result.decision, AccessDecision.DENY)
        self.assertIn("No face", result.reason)

    # 3. Multiple faces are denied
    def test_03_multiple_faces_denied(self):
        for count in [2, 3, 5]:
            result = evaluate_access(
                face_count=count,
                identity=self.authorized_user,
                liveness_verified=True,
                current_time=self.day_time,
                start_time_str=self.morning_start,
                end_time_str=self.evening_end,
            )
            self.assertEqual(result.decision, AccessDecision.DENY)
            self.assertIn("Multiple faces", result.reason)

    # 4. Failed liveness is denied
    def test_04_failed_liveness_denied(self):
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=False,
            current_time=self.day_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result.decision, AccessDecision.DENY)
        self.assertIn("Liveness", result.reason)

    # 5. Authorized identity during normal hours is granted
    def test_05_authorized_during_normal_hours_granted(self):
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=False,
            current_time=self.day_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result.decision, AccessDecision.GRANT)
        self.assertTrue(result.is_granted)
        self.assertIn("normal hours", result.reason)

    # 6. Authorized identity outside normal hours requires PIN
    def test_06_authorized_outside_normal_hours_requires_pin(self):
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=False,
            current_time=self.night_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result.decision, AccessDecision.REQUIRE_PIN)
        self.assertTrue(result.pin_required)
        self.assertIn("PIN", result.reason)

    # 7. Correct PIN outside normal hours grants access
    def test_07_correct_pin_outside_normal_hours_grants(self):
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(result.decision, AccessDecision.GRANT)
        self.assertTrue(result.is_granted)
        self.assertIn("verified PIN", result.reason)

    # 8. Incorrect PIN is denied
    def test_08_incorrect_pin_denied(self):
        is_valid = verify_pin(
            entered_pin="0000",
            configured_pin=self.test_pin
        )
        self.assertFalse(is_valid)

    # 9. Missing PIN is denied
    def test_09_missing_pin_denied(self):
        self.assertFalse(verify_pin(None, configured_pin=self.test_pin))
        self.assertFalse(verify_pin("", configured_pin=self.test_pin))
        self.assertFalse(verify_pin("   ", configured_pin=self.test_pin))

    # 10. Missing or placeholder PIN configuration fails closed
    def test_10_missing_or_placeholder_pin_config_fails_closed(self):
        placeholders = [
            None,
            "",
            "   ",
            "replace_with_a_private_numeric_pin",
            "your_pin_here",
            "placeholder",
            "changeme",
            "abc",     # non-numeric
            "12",      # too short (< 4 digits)
        ]
        for bad_pin in placeholders:
            self.assertFalse(
                is_valid_pin_configuration(bad_pin),
                f"Failed to reject invalid PIN config: {bad_pin}"
            )
            self.assertFalse(
                verify_pin("8492", configured_pin=bad_pin),
                f"verify_pin should fail closed for bad PIN config: {bad_pin}"
            )

    # 11. Invalid time configuration is rejected safely
    def test_11_invalid_time_configuration_rejected_safely(self):
        invalid_times = ["25:00", "12:60", "invalid", "", "8:30", "12:3"]
        for bad_time in invalid_times:
            with self.assertRaises(ValueError):
                parse_time_str(bad_time)

        # evaluate_access fails closed with DENY when given malformed times
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            current_time=self.day_time,
            start_time_str="25:99",
            end_time_str="22:00",
        )
        self.assertEqual(result.decision, AccessDecision.DENY)
        self.assertIn("Invalid access hours", result.reason)

    # 12. Normal window start boundary is handled correctly (start is inclusive)
    def test_12_normal_window_start_boundary_inclusive(self):
        start = "06:00"
        end = "22:00"
        # Exactly at start: 06:00:00 -> INCLUDED
        at_start = time(6, 0)
        self.assertTrue(is_within_normal_hours(at_start, start, end))

        # One minute before start: 05:59:00 -> EXCLUDED
        before_start = time(5, 59)
        self.assertFalse(is_within_normal_hours(before_start, start, end))

    # 13. Normal window end boundary is handled correctly (end is exclusive)
    def test_13_normal_window_end_boundary_exclusive(self):
        start = "06:00"
        end = "22:00"
        # One minute before end: 21:59:00 -> INCLUDED
        before_end = time(21, 59)
        self.assertTrue(is_within_normal_hours(before_end, start, end))

        # Exactly at end: 22:00:00 -> EXCLUDED
        at_end = time(22, 0)
        self.assertFalse(is_within_normal_hours(at_end, start, end))

    # 14. A normal window crossing midnight works correctly
    def test_14_normal_window_crossing_midnight(self):
        # Window: 22:00 to 06:00 (overnight shift)
        start = "22:00"
        end = "06:00"

        # Late night inside window (23:00)
        self.assertTrue(is_within_normal_hours(time(23, 0), start, end))
        # Start boundary inside window (22:00)
        self.assertTrue(is_within_normal_hours(time(22, 0), start, end))
        # Early morning inside window (03:30)
        self.assertTrue(is_within_normal_hours(time(3, 30), start, end))
        # Just before end boundary inside window (05:59)
        self.assertTrue(is_within_normal_hours(time(5, 59), start, end))

        # At end boundary outside window (06:00)
        self.assertFalse(is_within_normal_hours(time(6, 0), start, end))
        # Daytime outside window (12:00)
        self.assertFalse(is_within_normal_hours(time(12, 0), start, end))
        # Just before start boundary outside window (21:59)
        self.assertFalse(is_within_normal_hours(time(21, 59), start, end))

    # 15. Equal start and end values follow the explicitly documented policy
    def test_15_equal_start_and_end_treated_as_empty_window(self):
        start = "09:00"
        end = "09:00"

        # All times must return False (empty normal window)
        self.assertFalse(is_within_normal_hours(time(9, 0), start, end))
        self.assertFalse(is_within_normal_hours(time(12, 0), start, end))
        self.assertFalse(is_within_normal_hours(time(0, 0), start, end))

        # Evaluating access requires PIN because normal window is empty
        result = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=False,
            current_time=time(9, 0),
            start_time_str=start,
            end_time_str=end,
        )
        self.assertEqual(result.decision, AccessDecision.REQUIRE_PIN)

    # 16. A PIN cannot override any failed authentication condition
    def test_16_pin_cannot_override_failed_authentication(self):
        # Case A: pin_verified is True, but identity is Unknown
        res_unknown = evaluate_access(
            face_count=1,
            identity="Unknown",
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(res_unknown.decision, AccessDecision.DENY)

        # Case B: pin_verified is True, but multiple faces detected
        res_multi = evaluate_access(
            face_count=2,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(res_multi.decision, AccessDecision.DENY)

        # Case C: pin_verified is True, but liveness not verified
        res_no_liveness = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=False,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(res_no_liveness.decision, AccessDecision.DENY)

        # Case D: pin_verified is True, but zero faces
        res_zero = evaluate_access(
            face_count=0,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
        )
        self.assertEqual(res_zero.decision, AccessDecision.DENY)

    # 17. PIN verification is not reused across authentication attempts
    def test_17_pin_verification_not_reused_across_attempts(self):
        # First attempt: verified with PIN outside hours
        attempt1 = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=True,
            current_time=self.night_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(attempt1.decision, AccessDecision.GRANT)

        # Second attempt: new authentication without fresh PIN verification
        attempt2 = evaluate_access(
            face_count=1,
            identity=self.authorized_user,
            liveness_verified=True,
            pin_verified=False,  # reset for new attempt
            current_time=self.night_time,
            start_time_str=self.morning_start,
            end_time_str=self.evening_end,
        )
        self.assertEqual(attempt2.decision, AccessDecision.REQUIRE_PIN)


if __name__ == "__main__":
    unittest.main()
