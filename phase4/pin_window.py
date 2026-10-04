"""
Phase 4: Dedicated PIN Verification GUI Window for AI Smart Door Lock.

Provides a responsive, lightweight Tkinter PIN-entry window that operates
seamlessly alongside the OpenCV camera-processing loop without causing
frame drops, lag, or freezing.

Thread Safety
-------------
``_events`` and ``_is_visible`` are shared between the camera loop and
Tkinter callbacks.  Both are guarded by ``_lock`` (threading.Lock).
``poll_event()`` and ``update()`` acquire the lock before touching shared
state, making them safe to call from the main/camera thread.
"""

import threading
import tkinter as tk
from typing import Callable, List, Optional

from .access_control import verify_pin


class PinWindow:
    """
    Dedicated, non-blocking PIN verification dialog window.
    Designed to integrate into the main OpenCV camera loop via non-blocking
    event polling (`update()`), preserving full camera frame rate.
    """

    def __init__(
        self,
        validator: Callable[[str], bool] = verify_pin,
        title: str = "Secure Door Lock — PIN Verification",
    ):
        self._validator = validator
        self._title = title

        # Thread-safe shared state
        self._lock: threading.Lock = threading.Lock()
        self._is_visible: bool = False
        self._events: List[str] = []

        # Tkinter widgets (all None until _init_window succeeds)
        self._root: Optional[tk.Tk] = None
        self._entry_var: Optional[tk.StringVar] = None
        self._entry: Optional[tk.Entry] = None
        self._status_lbl: Optional[tk.Label] = None

        self._init_window()

    def _init_window(self) -> None:
        """Initializes the Tkinter window and UI widgets with dark theme."""
        try:
            self._root = tk.Tk()
        except tk.TclError:
            # Fallback for headless environments without a display server
            self._root = None
            return

        self._root.title(self._title)
        self._root.geometry("440x350")
        self._root.resizable(False, False)
        self._root.configure(bg="#1e1e24")

        # Keep window in front of fullscreen OpenCV window
        self._root.attributes("-topmost", True)

        # Start hidden/withdrawn
        self._root.withdraw()
        with self._lock:
            self._is_visible = False

        # Card container
        card = tk.Frame(
            self._root,
            bg="#282830",
            bd=0,
            padx=20,
            pady=20,
        )
        card.pack(fill="both", expand=True, padx=15, pady=15)

        # Header Title
        title_lbl = tk.Label(
            card,
            text="🔐  PIN REQUIRED",
            font=("Segoe UI", 13, "bold"),
            bg="#282830",
            fg="#ffffff",
        )
        title_lbl.pack(pady=(0, 4))

        # Subtitle Explanation
        subtitle_lbl = tk.Label(
            card,
            text="PIN verification is required outside normal access hours.",
            font=("Segoe UI", 9),
            bg="#282830",
            fg="#a0a0b0",
            wraplength=360,
        )
        subtitle_lbl.pack(pady=(0, 15))

        # Input Prompt Label
        prompt_lbl = tk.Label(
            card,
            text="Enter Security PIN:",
            font=("Segoe UI", 10, "bold"),
            bg="#282830",
            fg="#e0e0e0",
        )
        prompt_lbl.pack(anchor="w")

        # Masked PIN Entry
        self._entry_var = tk.StringVar()
        self._entry = tk.Entry(
            card,
            textvariable=self._entry_var,
            show="*",
            font=("Consolas", 18, "bold"),
            justify="center",
            bg="#16161a",
            fg="#00e5ff",
            insertbackground="#00e5ff",
            bd=2,
            relief="flat",
        )
        self._entry.pack(fill="x", ipady=6, pady=(4, 10))

        # Status Message Label
        self._status_lbl = tk.Label(
            card,
            text="🔒 PIN REQUIRED — please enter your PIN.",
            font=("Segoe UI", 9),
            bg="#282830",
            fg="#a0a0b0",
        )
        self._status_lbl.pack(pady=(0, 15))

        # Buttons Frame
        btn_frame = tk.Frame(card, bg="#282830")
        btn_frame.pack(fill="x")

        # Submit Button
        btn_submit = tk.Button(
            btn_frame,
            text="Submit",
            font=("Segoe UI", 10, "bold"),
            bg="#00b0ff",
            fg="#ffffff",
            activebackground="#0081cb",
            activeforeground="#ffffff",
            bd=0,
            padx=15,
            pady=7,
            cursor="hand2",
            command=self._on_submit,
        )
        btn_submit.pack(side="left", expand=True, fill="x", padx=(0, 5))

        # Cancel Button
        btn_cancel = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 10),
            bg="#3e3e4a",
            fg="#ffffff",
            activebackground="#525262",
            activeforeground="#ffffff",
            bd=0,
            padx=15,
            pady=7,
            cursor="hand2",
            command=self._on_cancel,
        )
        btn_cancel.pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Keyboard Bindings
        self._root.bind("<Return>", lambda e: self._on_submit())
        self._root.bind("<KP_Enter>", lambda e: self._on_submit())
        self._root.bind("<Escape>", lambda e: self._on_cancel())

        # Window close button handler
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _set_status(self, message: str, color: str) -> None:
        """Updates the status label text and color."""
        if self._status_lbl:
            self._status_lbl.config(text=message, fg=color)

    def _on_submit(self) -> None:
        """
        Handles submission from the Submit button click or Enter/KP_Enter keypress.

        Steps
        -----
        1. Read and immediately clear the PIN field (memory hygiene).
        2. If empty → prompt the user; do nothing else.
        3. Show "Verifying…" then call the validator.
        4. On success → display ``ACCESS GRANTED``, push ``"SUCCESS"``, schedule
           auto-hide after 350 ms.
        5. On failure → display ``ACCESS DENIED``, push ``"FAILED"``, keep window
           open so the user can retry.
        """
        if self._entry_var is None:
            return

        entered_pin = self._entry_var.get()
        # Immediately clear field to protect PIN confidentiality in memory/UI
        self._entry_var.set("")

        if not entered_pin:
            self._set_status("Please enter a PIN.", "#ffd600")
            return

        self._set_status("Verifying PIN...", "#ffd600")
        if self._root:
            self._root.update_idletasks()

        try:
            is_valid = self._validator(entered_pin)
        except Exception:
            is_valid = False

        if is_valid:
            self._set_status("✅  ACCESS GRANTED", "#00e676")
            with self._lock:
                self._events.append("SUCCESS")
            # Close dialog shortly after confirmation display
            if self._root:
                self._root.after(350, self.hide)
            else:
                self.hide()
        else:
            self._set_status("❌  ACCESS DENIED — incorrect PIN.", "#ff5252")
            with self._lock:
                self._events.append("FAILED")
            if self._entry:
                self._entry.focus_set()

    def _on_cancel(self) -> None:
        """
        Handles cancellation from the Cancel button, Escape key, or window close (×).
        Clears the PIN field, pushes ``"CANCELLED"``, and hides the window.
        """
        if self._entry_var:
            self._entry_var.set("")

        self._set_status("Verification cancelled.", "#a0a0b0")
        with self._lock:
            self._events.append("CANCELLED")
        self.hide()

    def show(self) -> None:
        """
        Opens (or brings focus to) the PIN window and resets its state.

        Safe to call when the window is already visible — it simply re-focuses
        and resets the entry field, preventing a second window from appearing.
        """
        with self._lock:
            self._is_visible = True
        self._set_status("🔒  PIN REQUIRED — please enter your PIN.", "#a0a0b0")

        if self._entry_var:
            self._entry_var.set("")

        if self._root:
            try:
                self._root.deiconify()
                self._root.lift()
                self._root.focus_force()
                if self._entry:
                    self._entry.focus_set()
            except Exception:
                pass

    def hide(self) -> None:
        """
        Hides the PIN window and clears the entry field.
        Thread-safe: updates ``_is_visible`` under the lock.
        """
        with self._lock:
            self._is_visible = False
        if self._entry_var:
            self._entry_var.set("")
        if self._root:
            try:
                self._root.withdraw()
            except Exception:
                pass

    def is_visible(self) -> bool:
        """
        Returns ``True`` if the PIN window is currently displayed.
        Thread-safe read under the lock.
        """
        with self._lock:
            return self._is_visible

    def poll_event(self) -> Optional[str]:
        """
        Drains the next pending event from the queue.

        Returns
        -------
        ``"SUCCESS"``, ``"FAILED"``, ``"CANCELLED"``, or ``None`` when the
        queue is empty.  Thread-safe — may be called from the camera/main
        thread at any time.
        """
        with self._lock:
            if self._events:
                return self._events.pop(0)
        return None

    def update(self) -> None:
        """
        Processes pending Tkinter events without blocking.

        Must be called once per camera loop iteration to keep the GUI
        responsive.  Calling it does not yield the GIL for more than a few
        microseconds, so frame rate is unaffected.
        """
        if self._root is not None:
            try:
                self._root.update_idletasks()
                self._root.update()
            except Exception:
                with self._lock:
                    self._is_visible = False

    def destroy(self) -> None:
        """Destroys the Tkinter window cleanly on application exit.
        Safe to call even if the window was never shown.
        """
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
            with self._lock:
                self._is_visible = False
