
---
# 1. Create a virtual environment
python -m venv venv

# 2. Activate it
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Create local configuration
Copy-Item .env.example .env

# 5. Run the application
python integration_test.py

-----------------------------------------------

# AI Smart Door Lock with Adaptive Security

A Computer Vision + Arduino based intelligent access-control system that combines **face recognition, liveness detection, and adaptive security decisions** to control a physical door lock.

> **Current progress:** Phase 1 + Phase 2 + Phase 3 + Phase 4 are integrated and working.  
> Arduino/servo hardware integration is planned for Phase 5.


## Project Overview

Traditional face-recognition locks generally make an access decision from identity alone.

This project uses a layered approach:

```text
Camera
   ↓
Face Detection
   ↓
Face Recognition
   ↓
Authorized?
   ↓
Liveness / Blink Detection
   ↓
Multiple-Face Security Check
   ↓
Adaptive Rules / Normal Hours Check
   ↓
PIN Required (If outside normal hours)
   ↓
Access Decision
   ↓
Future (Phase 5): Arduino + Servo Lock
```

The current system can:

- Detect a face through a webcam
- Recognize registered users
- Reject unknown users
- Detect multiple faces and deny access
- Perform blink-based liveness detection
- Require two blinks for liveness verification
- Check time-based access windows (`ACCESS_NORMAL_START` to `ACCESS_NORMAL_END`)
- Enforce secondary PIN verification outside normal hours (`DOOR_PIN`)
- Display the current identity, authorization, liveness, PIN challenge, and access state
- Reset authentication with a keyboard command (`R`)
- Open a dedicated Tkinter GUI PIN window with `P` (Submit, Cancel, Enter-key support)

---

## Novelty

The project is **not simply a face-recognition door lock**.

Its main idea is layered authentication:

1. **Identity verification** — Who is the person?
2. **Liveness verification** — Is this a real person rather than a static image?
3. **Multiple-face security** — Is more than one person attempting access?
4. **Adaptive authentication** — Contextual time rules and secondary PIN verification outside normal hours.
5. **Physical actuation** — Future Phase 5 will control the physical latch via Arduino + Servo.

The intended final decision is:

```text
Authorized Identity
        +
Liveness Verified
        +
Exactly One Face
        +
Normal Hours (OR Valid PIN)
        ↓
   Access Granted
```

---

## Current Implementation

### Phase 1 — Camera and Face Detection

- Webcam input using OpenCV
- Face detection
- Live camera processing

### Phase 2 — Face Recognition

- Registered face database
- Face encodings stored in `encodings.pkl`
- Authorized/unauthorized classification
- Recognition stabilization to reduce fluctuations during head movement

### Phase 3 — Liveness Detection

- MediaPipe Face Landmarker
- Eye landmark tracking
- Eye Aspect Ratio (EAR)
- Blink detection
- Two blinks required for liveness verification
- Liveness timeout
- Multiple-face rejection

### Phase 4 — Adaptive Security & Access Control

- Separate `phase4/access_control.py` module
- Dedicated non-blocking `phase4/pin_window.py` Tkinter GUI window replaces blocking `getpass()` terminal input
- Configurable normal access window (`ACCESS_NORMAL_START` to `ACCESS_NORMAL_END`)
- Secondary numeric PIN challenge outside normal access hours (`DOOR_PIN`)
- Cryptographically constant-time comparison (`hmac.compare_digest`)
- Anti-override enforcement (PIN never bypasses failed face recognition or failed liveness)
- Per-attempt state lifecycle (no PIN carry-over across attempts)
- Thread-safe event queue (`threading.Lock`) between camera loop and Tkinter callbacks
- Clear UI status labels: **PIN REQUIRED**, **ACCESS GRANTED**, **ACCESS DENIED**
- Automated unit test suite in `tests/test_access_control.py` and `tests/test_pin_window.py`

---

## Tech Stack

### AI / Computer Vision

- Python 3.11.9
- OpenCV 4.11.0.86
- MediaPipe 1.0.1
- face_recognition
- NumPy 1.26.4

### Configuration & Security

- `python-dotenv` for local `.env` environment loading
- `hmac` for constant-time PIN comparison

### Data

- Python Pickle (`.pkl`) for face encodings
- Image files in `phase2/known_faces/`

### Current Development

- VS Code
- Python virtual environment
- Git / GitHub

### Planned Hardware (Phase 5)

- Arduino Uno
- MG996R servo
- USB webcam
- LEDs
- Buzzer
- Push button
- Door/latch mechanism
- PySerial for Python-Arduino communication

---

## Project Structure

```text
AI-Smart-Door-Lock/
│
├── models/
│   ├── face_detector.task.tflite
│   └── face_landmarker.task
│
├── phase1/
│   └── camera_test.py
│
├── phase2/
│   ├── known_faces/
│   │   ├── Manisha.jpg
│   │   └── <other registered users>.jpg
│   │
│   ├── encodings.pkl
│   ├── register_faces.py
│   └── recognize_faces.py
│
├── phase3/
│   └── liveness_test.py
│
├── phase4/
│   ├── __init__.py
│   ├── access_control.py
│   └── pin_window.py
│
├── tests/
│   ├── __init__.py
│   ├── test_access_control.py
│   └── test_pin_window.py
│
├── integration_test.py
│
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
```

> The `venv/` directory should **not** be committed to GitHub.

---

# Setup Instructions

## 1. Clone the repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd AI-Smart-Door-Lock
```

---

## 2. Create a virtual environment

Windows:

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

You should see:

```text
(venv)
```

in your terminal.

---

## 3. Verify Python

This project currently uses:

```text
Python 3.11.9
```

Check your installation:

```powershell
python --version
```

---

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### Important: `face_recognition` / `dlib` on Windows

`face_recognition` depends on `dlib`.

On Windows, installing `face_recognition` may try to build `dlib` from source and fail if Visual C++ build tools are missing.

If this happens, install the required Visual C++ build environment or use the working installation method documented for your machine.

The project also requires the face-recognition model package.

If prompted by the installed package, install:

```powershell
pip install git+https://github.com/ageitgey/face_recognition_models
```

Then verify:

```powershell
python -c "import face_recognition; print('face_recognition OK')"
```

---

## 5. Verify MediaPipe

The project uses the MediaPipe Tasks API.

Check:

```powershell
python -c "import mediapipe as mp; print(mp.__version__)"
```

Expected:

```text
1.0.1
```

The project currently uses:

```text
mediapipe==1.0.1
```

and therefore uses:

```python
mp.tasks
```

rather than the older:

```python
mp.solutions
```

API.

---

# Required Model File

The Phase 3 liveness system requires:

```text
models/face_landmarker.task
```

Make sure this file exists before running the integrated program.

The expected path is:

```text
AI-Smart-Door-Lock/
└── models/
    └── face_landmarker.task
```

---

# Registering a New User

Registered face images are stored in:

```text
phase2/known_faces/
```

Add the new user's image there.

Example:

```text
phase2/
└── known_faces/
    ├── Manisha.jpg
    └── Rahul.jpg
```

Then regenerate the face database:

```powershell
python phase2/register_faces.py
```

This updates:

```text
phase2/encodings.pkl
```

Then run the integrated system again.

At startup, the program displays the registered users.

---

# Running the Current Integrated System

From the project root:

```powershell
python integration_test.py
```

The current system combines:

```text
Phase 1
Camera + Face Detection
        ↓
Phase 2
Face Recognition
        ↓
Phase 3
Liveness Detection
        ↓
Multiple-Face Security
        ↓
Access Decision
```

---

# Current Verification Behavior

### No face

```text
NO FACE
Waiting for person...
```

The identity and liveness state are reset.

### Unknown person

```text
Identity: Unknown
Status: UNAUTHORIZED
```

Access remains denied.

### Authorized person

```text
Identity: <registered name>
Status: AUTHORIZED
Liveness: BLINKS 0/2
```

The user must complete the liveness check.

### Liveness

The user performs two blinks:

```text
Blink 1
Blink 2
```

Then:

```text
Liveness: VERIFIED
```

### Access granted

The current integrated security condition is:

```text
Known identity
+
Liveness verified
+
Exactly one face
```

Then:

```text
ACCESS: GRANTED
```

### Multiple faces

If more than one face is detected:

```text
MULTIPLE FACES - ACCESS DENIED
```

Authentication and liveness are reset.

Even if one of the people is registered, access remains denied while multiple faces are visible.

---

# Keyboard Controls

While `integration_test.py` is running:

```text
Q → Quit
R → Reset authentication, liveness, and PIN state
P → Open dedicated GUI PIN window when challenged (outside normal access hours)
```

The PIN window has:
- A **masked input field** (characters shown as `*`)
- A **Submit** button (also triggered by the **Enter** key or numpad Enter)
- A **Cancel** button (also triggered by **Escape** or clicking the window's × button)

---

# Current Project Status

| Phase | Status |
|---|---|
| Phase 1 — Camera & Face Detection | ✅ Complete |
| Phase 2 — Face Recognition | ✅ Complete |
| Phase 3 — Liveness Detection | ✅ Complete |
| Phase 4 — Adaptive Security & Access Control | ✅ Complete |
| Phase 1 + 2 + 3 + 4 Integration | ✅ Complete |
| Phase 5 — Arduino + Servo | ⏳ Next |
| Phase 6 — Final Integration & Field Testing | ⏳ Planned |

---

# Phase 4 — Adaptive Security & Access Control

## 1. Purpose of Adaptive Security

Traditional biometric locks treat identity verification as a binary yes/no gate. The **Adaptive Security** layer adds contextual risk evaluation:

- **Normal Hours (Daytime)**: Authorized user + Verified liveness (blinks) = Direct access.
- **Off-Hours (Night/Weekend)**: Authorized user + Verified liveness + **Secondary PIN Verification** = Access granted.
- **Anti-Tailgating / Multiple Faces**: Immediate lockdown / denial regardless of time or PIN.
- **Fail-Closed Protection**: Any missing, malformed, or placeholder PIN configuration denies access.

```text
Normal Access Hours (e.g., 06:00 - 22:00)
       ↓
Authorized + Liveness Verified + Exactly 1 Face
       ↓
    ACCESS GRANTED


Outside Normal Hours (e.g., 22:00 - 06:00)
       ↓
Authorized + Liveness Verified + Exactly 1 Face
       ↓
  PIN CHALLENGE (Press 'P')
       ↓
  Correct PIN Verified
       ↓
    ACCESS GRANTED
```

> **Important**: A PIN can **never** override failed face recognition, failed liveness detection, or multiple detected faces.

---

## 2. Configuration & Secrets Setup

Configuration is managed via environment variables loaded by `python-dotenv`.

### Step 1: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 2: Create Local `.env`

Copy the template file to `.env`:

```powershell
copy .env.example .env
```

### Step 3: Configure `.env` Settings

Edit `.env` with your private parameters:

```dotenv
# Replace with a private numeric PIN (at least 4 digits)
DOOR_PIN=8492

# 24-hour format (HH:MM)
ACCESS_NORMAL_START=06:00
ACCESS_NORMAL_END=22:00
```

### Security Rules for Configuration:
- `.env` is listed in `.gitignore` and **must never be committed** to version control.
- Never place real PINs in `.env.example` or code.
- Placeholder values (e.g. `replace_with_a_private_numeric_pin`, empty strings, non-numeric strings, or <4 digits) are detected and fail closed (access denied).

---

## 3. Time Window Rules

The access control module (`phase4/access_control.py`) implements deterministic time evaluation:

- **24-hour format**: `HH:MM` (validated via strict regex).
- **Inclusive start, exclusive end**: `[start, end)`. For example, `06:00` to `22:00` includes `06:00:00` and excludes `22:00:00`.
- **Overnight windows supported**: Windows that cross midnight (e.g., `22:00` to `06:00`) are handled properly (times $\ge$ 22:00 or $<$ 06:00 are normal hours).
- **Equal start and end values**: Explicit policy treats `start == end` as an empty normal window (duration 0). All times are considered outside normal hours and require a PIN.

---

## 4. Running Automated Unit Tests

A comprehensive suite of **30 automated tests** is provided across `tests/test_access_control.py` and `tests/test_pin_window.py`. These test access control rules, boundary conditions, time windows, and non-blocking GUI event polling deterministically.

Run tests:

```powershell
python -m unittest discover -s tests -v
```

The test suites validate:
1. Unknown/unauthorized identity denial
2. Zero faces denial
3. Multiple faces denial (anti-tailgating)
4. Failed liveness denial
5. Authorized identity during normal hours granted
6. Authorized identity outside normal hours requires PIN
7. Correct PIN outside normal hours grants access
8. Incorrect PIN denied
9. Missing PIN denied
10. Missing/placeholder PIN configuration fails closed
11. Invalid time configuration safely rejected
12. Normal window start boundary (inclusive)
13. Normal window end boundary (exclusive)
14. Midnight-crossing windows
15. Equal start and end treated as empty window
16. PIN cannot override any failed authentication condition
17. PIN verification not reused across separate attempts
18. Non-blocking event-polling update does not freeze camera loop
19. Only one PIN window instance active at a time
20. Correct PIN → `SUCCESS` event + `ACCESS GRANTED` status label
21. Incorrect PIN entry → `FAILED` event + `ACCESS DENIED` status label
22. GUI cancellation → `CANCELLED` event, window hidden, access not granted
23. Resetting authentication clears PIN authorization and hides window
24. Liveness loss and multi-face alerts invalidate PIN authorization
25. Identity changes invalidate PIN authorization
26. Placeholder or invalid PIN configuration fails closed in GUI
27. Clean shutdown behavior with PIN window active
28. Submit button label present (not "Verify PIN")
29. Status labels display `PIN REQUIRED`, `ACCESS GRANTED`, `ACCESS DENIED` correctly
30. Thread-safe `poll_event()` under concurrent producer/consumer access

---

## 5. Running the Integrated System

To launch the full Phase 1–4 integrated application:

```powershell
python integration_test.py
```

### Dedicated GUI PIN Window & Non-Blocking Operation:
- When an authorized, live face is detected outside normal access hours, the UI displays `ACCESS: PIN REQUIRED (PRESS P)`.
- Pressing **`P`** opens a dedicated, masked Tkinter GUI window (`Secure Door Lock — PIN Verification`) floating above the camera feed.
- **Zero Camera Lag**: The camera loop continuously processes frames at full speed without freezing, allowing face tracking and liveness monitoring to remain active while the user types.
- The user can type their PIN and press **Enter** (or click **Submit**). Keystrokes are masked (`*`).
- **Status labels** show `🔒 PIN REQUIRED` when the window opens, `✅ ACCESS GRANTED` on success, and `❌ ACCESS DENIED` on failure.
- Pressing **Escape** or clicking **Cancel** closes the window and cancels the challenge.
- If the user steps away, another face enters, liveness expires, or the reset key **`R`** is pressed, the PIN window is automatically closed and any pending verification state is wiped immediately.
- A `threading.Lock` guards the event queue so the camera-loop thread and Tkinter callbacks never race.

> **Hardware Actuation Notice**: Hardware actuation (Arduino Uno, MG996R servo, relays, physical door lock mechanism, LEDs, buzzer) is **not** part of Phase 4 and is planned for Phase 5.


---

# Planned Hardware Integration

The final system will connect Python to an Arduino:

```text
Python AI System
       ↓
    PySerial
       ↓
 Arduino Uno
       ↓
 ┌─────┼─────┐
 ↓     ↓     ↓
Servo  LED  Buzzer
 ↓
Door Lock
```

Expected behavior:

```text
UNLOCK
  ↓
Servo rotates
  ↓
Door unlocks
  ↓
Wait
  ↓
Servo returns
  ↓
Door locks
```

---

# Security Considerations

This is an educational prototype and should not be treated as production-grade physical security.

Current limitations include:

- Webcam-based recognition
- Software-based face database
- Blink-based liveness detection
- No encrypted credential storage
- No production-grade anti-spoofing model
- No secure authentication of the Python-Arduino serial link yet

The project is intended to demonstrate the integration of AI, computer vision, and embedded hardware.

---

# Author / Project

**AI Smart Door Lock with Adaptive Security**

A college project demonstrating:

- Artificial Intelligence
- Computer Vision
- Face Recognition
- Liveness Detection
- Embedded Systems
- Security Decision Making
- Hardware Control
- Python
- Arduino

---

## License

This project is intended for educational and demonstration purposes.
