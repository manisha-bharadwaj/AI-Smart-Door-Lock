# AI Smart Door Lock with Adaptive Security

A Computer Vision + Arduino based intelligent access-control system that combines **face recognition, liveness detection, and adaptive security decisions** to control a physical door lock.

> **Current progress:** Phase 1 + Phase 2 + Phase 3 are integrated and working.  
> Arduino/servo hardware integration and adaptive time/PIN rules are planned for later phases.

---

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
Access Decision
   ↓
Future: Context / PIN
   ↓
Future: Arduino + Servo Lock
```

The current system can:

- Detect a face through a webcam
- Recognize registered users
- Reject unknown users
- Detect multiple faces and deny access
- Perform blink-based liveness detection
- Require two blinks for liveness verification
- Display the current identity, authorization, liveness, and access state
- Reset authentication with a keyboard command

---

## Novelty

The project is **not simply a face-recognition door lock**.

Its main idea is layered authentication:

1. **Identity verification** — Who is the person?
2. **Liveness verification** — Is this a real person rather than a static image?
3. **Multiple-face security** — Is more than one person attempting access?
4. **Adaptive authentication** — Future phases will add context such as access time and an additional PIN.

The intended final decision is:

```text
Authorized Identity
        +
Liveness Verified
        +
Exactly One Face
        +
Context Rules
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

---

## Tech Stack

### AI / Computer Vision

- Python 3.11.9
- OpenCV 4.11.0.86
- MediaPipe 1.0.1
- face_recognition
- NumPy 1.26.4

### Data

- Python Pickle (`.pkl`) for face encodings
- Image files in `phase2/known_faces/`

### Current Development

- VS Code
- Python virtual environment
- Git / GitHub

### Planned Hardware

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
├── integration_test.py
│
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
R → Reset authentication/liveness
```

---

# Current Project Status

| Phase | Status |
|---|---|
| Phase 1 — Camera & Face Detection | ✅ Complete |
| Phase 2 — Face Recognition | ✅ Complete |
| Phase 3 — Liveness Detection | ✅ Complete |
| Phase 1 + 2 + 3 Integration | ✅ Complete |
| Phase 4 — Adaptive Security | ⏳ Next |
| Phase 5 — Arduino + Servo | ⏳ Planned |
| Phase 6 — Final Integration & Testing | ⏳ Planned |

---

# Planned Phase 4

The next phase will introduce adaptive authentication.

Example:

```text
Normal daytime
      ↓
Authorized + Live
      ↓
Access Granted


Late-night access
      ↓
Authorized + Live
      ↓
Additional PIN
      ↓
Access Granted
```

This will make the system context-aware instead of relying only on identity.

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
