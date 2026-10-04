"""
Phase 4: Adaptive Access-Control Layer for AI Smart Door Lock.

Enforces layered security rules:
1. Exactly one face must be detected.
2. The detected face must match an authorized registered user.
3. Liveness (blink verification) must be verified.
4. If within normal access hours, access is GRANTED directly.
5. If outside normal access hours, PIN verification is REQUIRED.
6. Outside normal access hours, access is GRANTED only after successful PIN verification.
7. Any missing, incorrect, or unconfigured PIN fails closed.
"""

import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Iterable, Optional, Union

from dotenv import load_dotenv

# Load local environment configuration
load_dotenv()

# Precompiled regex for 24-hour time validation (HH:MM)
TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# Known placeholder PIN values that must never be considered valid configurations
PLACEHOLDER_PINS = {
    "replace_with_a_private_numeric_pin",
    "your_pin_here",
    "placeholder",
    "changeme",
    "pin_here",
}


class AccessDecision(str, Enum):
    """
    Possible access decisions produced by the adaptive security layer.
    """
    GRANT = "GRANT"
    DENY = "DENY"
    REQUIRE_PIN = "REQUIRE_PIN"


@dataclass(frozen=True)
class AccessResult:
    """
    Represents the evaluation outcome with decision and a human-readable reason.
    """
    decision: AccessDecision
    reason: str

    @property
    def is_granted(self) -> bool:
        return self.decision == AccessDecision.GRANT

    @property
    def is_denied(self) -> bool:
        return self.decision == AccessDecision.DENY

    @property
    def pin_required(self) -> bool:
        return self.decision == AccessDecision.REQUIRE_PIN


def parse_time_str(time_str: str) -> time:
    """
    Parses and validates a 24-hour time string in HH:MM format into a datetime.time object.

    Raises:
        ValueError: If time_str is malformed, out of range, or not a string.
    """
    if not isinstance(time_str, str):
        raise ValueError(f"Time value must be a string, got {type(time_str).__name__}")

    match = TIME_REGEX.match(time_str.strip())
    if not match:
        raise ValueError(
            f"Invalid time format '{time_str}'. Expected 24-hour 'HH:MM' format between 00:00 and 23:59."
        )

    hour = int(match.group(1))
    minute = int(match.group(2))
    return time(hour=hour, minute=minute)


def is_within_normal_hours(
    check_time: time,
    start: Union[time, str],
    end: Union[time, str]
) -> bool:
    """
    Checks if check_time falls within the normal access window [start, end).
    Start is inclusive, end is exclusive.

    Rules:
    - start < end: Standard daytime window within the same calendar day (e.g., 06:00 to 22:00).
    - start > end: Overnight window spanning past midnight (e.g., 22:00 to 06:00).
    - start == end: Explicit policy: Identical start and end defines an empty window (0 duration),
      meaning no time falls within normal hours, and PIN verification is always required.
    """
    if isinstance(start, str):
        start = parse_time_str(start)
    if isinstance(end, str):
        end = parse_time_str(end)

    if start == end:
        # Policy: Equal boundaries represent an empty normal window
        return False
    elif start < end:
        return start <= check_time < end
    else:
        # Window spans across midnight
        return check_time >= start or check_time < end


def is_valid_pin_configuration(configured_pin: Optional[str]) -> bool:
    """
    Validates whether a configured DOOR_PIN string is safe and valid.
    Fails closed if the PIN is None, empty, whitespace, non-numeric, too short (< 4 digits),
    or matches a known placeholder.
    """
    if not configured_pin or not isinstance(configured_pin, str):
        return False

    pin_clean = configured_pin.strip()
    if not pin_clean:
        return False

    if pin_clean.lower() in PLACEHOLDER_PINS:
        return False

    # PIN must be numeric and at least 4 digits
    if not pin_clean.isdigit() or len(pin_clean) < 4:
        return False

    return True


def verify_pin(
    entered_pin: Optional[str],
    configured_pin: Optional[str] = None
) -> bool:
    """
    Securely verifies a user-entered PIN against the configured DOOR_PIN using
    constant-time comparison (hmac.compare_digest) to prevent timing attacks.

    Fails closed (returns False) if:
    - Configured PIN is missing, invalid, or placeholder.
    - Entered PIN is None, empty, or non-string.
    - Entered PIN does not match configured PIN.
    """
    if configured_pin is None:
        configured_pin = os.getenv("DOOR_PIN")

    if not is_valid_pin_configuration(configured_pin):
        return False

    if entered_pin is None or not isinstance(entered_pin, str):
        return False

    entered_clean = entered_pin.strip()
    configured_clean = configured_pin.strip()  # type: ignore[union-attr]

    if not entered_clean:
        return False

    return hmac.compare_digest(
        entered_clean.encode("utf-8"),
        configured_clean.encode("utf-8")
    )


def evaluate_access(
    face_count: int,
    identity: Optional[str],
    liveness_verified: bool,
    pin_verified: bool = False,
    current_time: Optional[time] = None,
    authorized_names: Optional[Iterable[str]] = None,
    start_time_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
) -> AccessResult:
    """
    Evaluates the complete access request according to Phase 4 Adaptive Security rules.

    Mandatory Rules Evaluated in Strict Order:
    1. If the number of detected faces != 1 -> DENY.
    2. If the detected identity is unknown or unauthorized -> DENY.
    3. If liveness verification has not passed -> DENY.
    4. If current time is within normal access hours -> GRANT.
    5. If outside normal access hours:
       - If PIN has been verified for this attempt -> GRANT.
       - Otherwise -> REQUIRE_PIN.

    A PIN can NEVER override rules 1, 2, or 3.
    """
    # Rule 1: Exactly one face
    if face_count == 0:
        return AccessResult(AccessDecision.DENY, "No face detected")
    if face_count > 1:
        return AccessResult(AccessDecision.DENY, f"Multiple faces detected ({face_count})")

    # Rule 2: Authorized identity
    if not identity or identity == "Unknown":
        return AccessResult(AccessDecision.DENY, "Unauthorized identity: Unknown")
    if authorized_names is not None and identity not in authorized_names:
        return AccessResult(AccessDecision.DENY, f"Unauthorized identity: {identity}")

    # Rule 3: Liveness verified
    if not liveness_verified:
        return AccessResult(AccessDecision.DENY, "Liveness verification required")

    # Determine time
    if current_time is None:
        current_time = datetime.now().time()

    start_str = start_time_str or os.getenv("ACCESS_NORMAL_START", "06:00")
    end_str = end_time_str or os.getenv("ACCESS_NORMAL_END", "22:00")

    try:
        within_hours = is_within_normal_hours(current_time, start_str, end_str)
    except ValueError as e:
        # Invalid time configuration fails closed
        return AccessResult(AccessDecision.DENY, f"Invalid access hours configuration: {e}")

    # Rule 4: Normal access hours
    if within_hours:
        return AccessResult(AccessDecision.GRANT, "Authorized access during normal hours")

    # Rule 5 & 6: Outside normal access hours requires PIN
    if pin_verified:
        return AccessResult(
            AccessDecision.GRANT,
            "Authorized access outside normal hours with verified PIN"
        )
    else:
        return AccessResult(
            AccessDecision.REQUIRE_PIN,
            "PIN verification required outside normal hours"
        )
