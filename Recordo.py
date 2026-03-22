import pyautogui
import keyboard
import mouse
import math
import time
import threading
import random
import json
import os
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

#-----------------------------
#Save settings to file
#-----------------------------
SETTINGS_FILE = "recordo_settings.json"

settings = {
    "offset_range": 5,
    "timing_jitter": 0,
    
    "tier1_distance": 350,
    "tier2_distance": 700,

    "tier1_min": 0.10,
    "tier1_max": 0.25,

    "tier2_min": 0.25,
    "tier2_max": 0.55,

    "tier3_min": 0.55,
    "tier3_max": 1.20,
    
    "curve_intensity": 50
}

def load_settings():
    global settings
    global OFFSET_RANGE, TIMING_JITTER, CURVE_INTENSITY
    global TIER1_DISTANCE, TIER2_DISTANCE
    global TIER1_MIN, TIER1_MAX
    global TIER2_MIN, TIER2_MAX
    global TIER3_MIN, TIER3_MAX

    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)

    OFFSET_RANGE = settings.get("offset_range", 5)
    TIMING_JITTER = settings.get("timing_jitter", 0)
    CURVE_INTENSITY = settings.get("curve_intensity", 50)

    # Movement tiers
    TIER1_DISTANCE = settings.get("tier1_distance", 350)
    TIER2_DISTANCE = settings.get("tier2_distance", 700)

    TIER1_MIN = settings.get("tier1_min", 0.10)
    TIER1_MAX = settings.get("tier1_max", 0.25)

    TIER2_MIN = settings.get("tier2_min", 0.25)
    TIER2_MAX = settings.get("tier2_max", 0.55)

    TIER3_MIN = settings.get("tier3_min", 0.55)
    TIER3_MAX = settings.get("tier3_max", 1.20)


def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


load_settings()

# -----------------------------
# Global State
# -----------------------------
recording = False
playing = False
recorded_events = []
record_start_time = 0

record_thread = None
play_thread = None

# These are already set by load_settings(), but you can keep these lines if you want:
TIMING_JITTER = settings.get("timing_jitter", 0)
OFFSET_RANGE = settings.get("offset_range", 5)
CURVE_INTENSITY = settings.get("curve_intensity", 50)



# -----------------------------
#  Stop playback on window close
# -----------------------------
def on_close():
    global playing, recording
    playing = False
    recording = False
    root.destroy()


# -----------------------------
# Recording Logic
# -----------------------------
def record_events():
    global recording, recorded_events, record_start_time

    recorded_events = []
    record_start_time = time.time()

    while recording:
        now = time.time() - record_start_time

        # Left click
        if mouse.is_pressed(button="left"):
            x, y = pyautogui.position()
            recorded_events.append(("click_left", now, (x, y)))
            time.sleep(0.15)

        # Right click
        if mouse.is_pressed(button="right"):
            x, y = pyautogui.position()
            recorded_events.append(("click_right", now, (x, y)))
            time.sleep(0.15)

        # Keyboard keys
        for key in "abcdefghijklmnopqrstuvwxyz1234567890":
            if keyboard.is_pressed(key):
                recorded_events.append(("key", now, key))
                time.sleep(0.15)

        time.sleep(0.01)

#-----------------------------
# Windows SendInput mouse movement
#-----------------------------

SendInput = ctypes.windll.user32.SendInput

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def move_mouse_absolute(x, y):
    """Move mouse using absolute positioning (0–65535 range)."""
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)

    abs_x = int(x * 65535 / screen_w)
    abs_y = int(y * 65535 / screen_h)

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            class _MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", ctypes.c_long),
                    ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]
            _fields_ = [("mi", _MOUSEINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _INPUT)]

    inp = INPUT()
    inp.type = 0  # INPUT_MOUSE
    inp.mi.dx = abs_x
    inp.mi.dy = abs_y
    inp.mi.dwFlags = 0x8000 | 0x0001  # MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE

    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

#-----------------------------
# Mouse Movement Curves
#-----------------------------
def move_mouse_curve(x1, y1, x2, y2, duration=0.6, steps=33):
    """Smooth, human-like curved mouse movement with larger arcs."""

    global playing

   # Distance between points
    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)

    # Apply distance-based curve strength
    if distance < 100:
        base_strength = random.randint(5, 20)
    elif distance < 300:
        base_strength = random.randint(20, 70)
    else:
        base_strength = random.randint(70, 150)

    # Apply user intensity (0–100)
    intensity_scale = CURVE_INTENSITY / 50.0   # 50 = neutral
    curve_strength = base_strength * intensity_scale



    # Pick a random angle for the curve direction
    angle = random.uniform(0, 3.14)

    cx1 = x1 + math.cos(angle) * curve_strength
    cy1 = y1 + math.sin(angle) * curve_strength

    cx2 = x2 + math.cos(angle + random.uniform(-0.6, 0.6)) * curve_strength
    cy2 = y2 + math.sin(angle + random.uniform(-0.6, 0.6)) * curve_strength

    start = time.time()

    for i in range(steps + 1):

       # Stop playback immediately if user pressed Stop
        if not playing:
            return

        t = i / steps

        # Ease-in-out
        t = t * t * (3 - 2 * t)

        # Cubic Bezier
        x = (1-t)**3 * x1 + 3*(1-t)**2 * t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * x2
        y = (1-t)**3 * y1 + 3*(1-t)**2 * t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * y2

        move_mouse_absolute(int(x), int(y))

        # Keep timing consistent
        elapsed = time.time() - start
        target = (i / steps) * duration
        sleep_time = target - elapsed
        if sleep_time > 0:
            if not playing:
                return
            time.sleep(sleep_time)



# -----------------------------
# Playback Logic
# -----------------------------
def play_events():
    global playing

    while playing:
        start_time = time.time()

        for event in recorded_events:
            if not playing:
                break

            etype, timestamp, data = event

            # -----------------------------
            # KEYBOARD EVENTS
            # -----------------------------
            if etype == "key":
                now = time.time() - start_time
                delay = timestamp - now

                if TIMING_JITTER > 0:
                    jitter = random.uniform(-TIMING_JITTER/1000, TIMING_JITTER/1000)
                    delay += jitter

                if delay > 0:
                    time.sleep(delay)

                keyboard.press_and_release(data)
                continue

            # -----------------------------
            # MOUSE CLICKS (movement scheduled to land on time)
            # -----------------------------
            if etype in ("click_left", "click_right"):
                x, y = data

                # Apply offset
                offset_x = random.randint(-OFFSET_RANGE, OFFSET_RANGE)
                offset_y = random.randint(-OFFSET_RANGE, OFFSET_RANGE)
                target_x = x + offset_x
                target_y = y + offset_y

                # Base scheduled click time
                scheduled_time = timestamp

                # Apply jitter to click time
                if TIMING_JITTER > 0:
                    scheduled_time += random.uniform(-TIMING_JITTER/1000, TIMING_JITTER/1000)
                    
                # Get current mouse position BEFORE computing distance
                current_x, current_y = pyautogui.position()


                # Random movement duration
                # Distance-based movement duration
                dx = target_x - current_x
                dy = target_y - current_y
                distance = math.hypot(dx, dy)

                if distance < TIER1_DISTANCE:
                    duration = random.uniform(TIER1_MIN, TIER1_MAX)
                elif distance < TIER2_DISTANCE:
                    duration = random.uniform(TIER2_MIN, TIER2_MAX)
                else:
                    duration = random.uniform(TIER3_MIN, TIER3_MAX)

                # When movement must begin
                movement_start_time = scheduled_time - duration

                # Wait until movement start time
                now = time.time() - start_time
                delay = movement_start_time - now
                if delay > 0:
                    time.sleep(delay)

                # Move

                move_mouse_curve(current_x, current_y, target_x, target_y, duration=duration)

                if not playing:
                    return

                # Click immediately on arrival
                if etype == "click_left":
                    pyautogui.click()
                else:
                    pyautogui.rightClick()

# -----------------------------
# Save / Load
# -----------------------------
def save_recording():
    if not recorded_events:
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json")]
    )
    if not file_path:
        return

    with open(file_path, "w") as f:
        json.dump(recorded_events, f)

def load_recording():
    global recorded_events

    file_path = filedialog.askopenfilename(
        filetypes=[("JSON Files", "*.json")]
    )
    if not file_path:
        return

    with open(file_path, "r") as f:
        recorded_events = json.load(f)

# -----------------------------
# Toggle Functions
# -----------------------------
def toggle_record():
    global recording, record_thread

    if not recording:
        recording = True
        record_status_label.config(text="Recording: ON", fg="red")
        record_thread = threading.Thread(target=record_events)
        record_thread.start()
    else:
        recording = False
        record_thread.join()
        record_status_label.config(text="Recording: OFF", fg="black")

def toggle_play():
    global playing, play_thread

    if not recorded_events:
        return

    if not playing:
        playing = True
        play_status_label.config(text="Playing: ON", fg="green")
        play_thread = threading.Thread(target=play_events, daemon=True)
        play_thread.start()
    else:
        playing = False
        play_thread.join()
        play_status_label.config(text="Playing: OFF", fg="black")

# -----------------------------
# Hotkeys
# -----------------------------
keyboard.add_hotkey("F10", toggle_record)
keyboard.add_hotkey("F8", toggle_play)

# -----------------------------
# GUI
# -----------------------------
root = tk.Tk()

root.protocol("WM_DELETE_WINDOW", on_close) # Ensure we stop threads when closing the window


# --- Dark Theme Colors ---
BG = "#1e1e1e"        # main background
FG = "#ffffff"        # main text
BTN_BG = "#2d2d2d"    # button background
BTN_FG = "#ffffff"    # button text
ENTRY_BG = "#2b2b2b"  # entry background
ENTRY_FG = "#ffffff"  # entry text
FRAME_BG = "#252525"  # advanced panel background

root.configure(bg=BG)

root.title("Recordo")
root.geometry("270x300")
root.resizable(False, True)
root.update_idletasks()

# --- Tab styles ---

style = ttk.Style()
style.theme_use("default")

# Notebook background (the area behind tabs)
style.configure("TNotebook",
                background=FRAME_BG,
                borderwidth=0)

# Unselected tabs
style.configure("TNotebook.Tab",
                background="#555555",   # slightly lighter grey
                foreground=FG,
                padding=[10, 5])

# Selected tab
style.map("TNotebook.Tab",
          background=[("selected", "#2d2d2d")],   # brighter highlight
          foreground=[("selected", FG)])


# Hover effect for tabs
style.map("TNotebook.Tab",
    background=[
        ("selected", "#0d8fda"),
        ("active", "#0412d3")   # hover color
    ],
    foreground=[
        ("selected", FG),
        ("active", FG)
    ]
)



# --- Dark Title Bar (Windows only) ---
try:
    import ctypes
    HWND = ctypes.windll.user32.GetParent(root.winfo_id())
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        HWND,
        DWMWA_USE_IMMERSIVE_DARK_MODE,
        ctypes.byref(ctypes.c_int(1)),
        ctypes.sizeof(ctypes.c_int(1))
    )
except Exception:
    pass  # Ignore if not on Windows or unsupported


# Add hover effect to buttons
def add_hover_effect(widget):
    widget.bind("<Enter>", lambda e: widget.config(bg="#3a3a3a"))
    widget.bind("<Leave>", lambda e: widget.config(bg=BTN_BG))

#Advanced settings panel

advanced_visible = False

def toggle_advanced():
    global advanced_visible
    advanced_visible = not advanced_visible

    if advanced_visible:
        advanced_frame.pack(pady=5)
        advanced_button.config(text="Advanced Settings ▲")

        # Let Tkinter auto-resize to fit the panel
        root.update_idletasks()
        new_height = root.winfo_reqheight()
        root.geometry(f"270x{new_height}")

    else:
        advanced_frame.pack_forget()
        advanced_button.config(text="Advanced Settings ▼")

        # Force window back to compact size
        root.geometry("270x300")


# Start always on top
root.attributes("-topmost", True)

# Checkbox state
always_on_top_var = tk.BooleanVar(value=True)

def toggle_always_on_top():
    root.attributes("-topmost", always_on_top_var.get())

title_label = tk.Label(root, text="Recordo", font=("Arial", 14, "bold"), bg=BG, fg=FG)
title_label.pack(pady=10)

record_button = tk.Button(root, text="Record (F10)", width=20, command=toggle_record, bg=BTN_BG, fg=BTN_FG,
                          activebackground="#3a3a3a", activeforeground=FG)

record_button.pack(pady=5)

record_status_label = tk.Label(root, text="Recording: OFF", font=("Arial", 10), bg=BG, fg=FG)
record_status_label.pack()

play_button = tk.Button(root, text="Play (F8)", width=20, command=toggle_play, bg=BTN_BG, fg=BTN_FG,
                          activebackground="#3a3a3a", activeforeground=FG)
play_button.pack(pady=5)

play_status_label = tk.Label(root, text="Playing: OFF", font=("Arial", 10), bg=BG, fg=FG)
play_status_label.pack()

save_button = tk.Button(root, text="Save Recording", width=20, command=save_recording, bg=BTN_BG, fg=BTN_FG,
                          activebackground="#3a3a3a", activeforeground=FG)
save_button.pack(pady=10)

load_button = tk.Button(root, text="Load Recording", width=20, command=load_recording, bg=BTN_BG, fg=BTN_FG,
                          activebackground="#3a3a3a", activeforeground=FG)
load_button.pack()

# Always on top checkbox (moved up)
always_on_top_checkbox = tk.Checkbutton(
    root,
    text="Always on Top",
    variable=always_on_top_var,
    command=toggle_always_on_top,
    bg=BG,
    fg=FG,
    activebackground=BG,
    activeforeground=FG,
    selectcolor=BG
)
always_on_top_checkbox.pack(pady=5)

# Advanced settings toggle button

advanced_button = tk.Button(root, text="Advanced Settings ▼", width=20, command=toggle_advanced, bg=BTN_BG, fg=BTN_FG,
                          activebackground="#3a3a3a", activeforeground=FG)
advanced_button.pack(pady=5)

advanced_frame = tk.Frame(root, borderwidth=1, relief="solid", bg=FRAME_BG)

#Call function to add hover effect to buttons place after last button is created to avoid error
add_hover_effect(record_button)
add_hover_effect(play_button)
add_hover_effect(save_button)
add_hover_effect(load_button)
add_hover_effect(advanced_button)



# -----------------------------
# Advanced Settings (Tabbed)
# -----------------------------

# Create notebook (tabs)
notebook = ttk.Notebook(advanced_frame)
notebook.pack(fill="both", expand=True, padx=5, pady=5)

# Create tab frames
movement_tab = tk.Frame(notebook, bg=FRAME_BG)
click_tab = tk.Frame(notebook, bg=FRAME_BG)

notebook.add(movement_tab, text="Movement")
notebook.add(click_tab, text="Clicks")

# -----------------------------
# MOVEMENT TAB
# -----------------------------

# --- Curve Intensity ---
curve_label = tk.Label(movement_tab, text="Curve Intensity (0–100):", bg=FRAME_BG, fg=FG)
curve_label.pack(pady=(5,0))

curve_entry = tk.Entry(movement_tab, width=10,
                       bg=ENTRY_BG, fg=ENTRY_FG,
                       insertbackground=FG)
curve_entry.insert(0, str(settings.get("curve_intensity", 50)))
curve_entry.pack(pady=(0,5))

def update_curve_intensity(event=None):
    global CURVE_INTENSITY
    try:
        value = int(curve_entry.get())
        value = max(0, min(100, value))
        settings["curve_intensity"] = value
        CURVE_INTENSITY = value
        save_settings()
    except ValueError:
        pass

curve_entry.bind("<KeyRelease>", update_curve_intensity)


# -----------------------------
# Movement Tiers
# -----------------------------
tiers_frame = tk.LabelFrame(movement_tab, text="Movement Tiers", bg=FRAME_BG, fg=FG)
tiers_frame.pack(fill="x", pady=10, padx=5)


def make_tier(title, distance_label, dist_value, min_value, max_value):
    # Title
    tk.Label(tiers_frame, text=title, bg=FRAME_BG, fg=FG, font=("Arial", 10, "bold")).pack(anchor="w", pady=(8,2))

    # Distance row
    dist_row = tk.Frame(tiers_frame, bg=FRAME_BG)
    dist_row.pack(anchor="w", pady=1)

    tk.Label(dist_row, text=distance_label, bg=FRAME_BG, fg=FG).pack(side="left")
    dist_entry = tk.Entry(dist_row, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG)
    dist_entry.insert(0, str(dist_value))
    dist_entry.pack(side="left", padx=5)

    # Min/Max row
    mm_row = tk.Frame(tiers_frame, bg=FRAME_BG)
    mm_row.pack(anchor="w", pady=1)

    tk.Label(mm_row, text="Min", bg=FRAME_BG, fg=FG).pack(side="left")
    min_entry = tk.Entry(mm_row, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG)
    min_entry.insert(0, str(min_value))
    min_entry.pack(side="left", padx=5)

    tk.Label(mm_row, text="Max", bg=FRAME_BG, fg=FG).pack(side="left")
    max_entry = tk.Entry(mm_row, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG)
    max_entry.insert(0, str(max_value))
    max_entry.pack(side="left", padx=5)

    return dist_entry, min_entry, max_entry


# Tier 1
tier1_dist, tier1_min, tier1_max = make_tier(
    "Tier 1 (Short Distance)",
    "Distance <",
    settings.get("tier1_distance", 350),
    settings.get("tier1_min", 0.10),
    settings.get("tier1_max", 0.25)
)

# Tier 2
tier2_dist, tier2_min, tier2_max = make_tier(
    "Tier 2 (Medium Distance)",
    "Distance <",
    settings.get("tier2_distance", 700),
    settings.get("tier2_min", 0.25),
    settings.get("tier2_max", 0.55)
)

# Tier 3
tk.Label(tiers_frame, text="Tier 3 (Long Distance)", bg=FRAME_BG, fg=FG, font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,2))

tier3_info = tk.Label(tiers_frame,
                      text=f"Distance ≥ Tier 2 ({settings.get('tier2_distance', 700)})",
                      bg=FRAME_BG, fg="#bbbbbb")
tier3_info.pack(anchor="w", pady=(0,4))


tier3_minmax = tk.Frame(tiers_frame, bg=FRAME_BG)
tier3_minmax.pack(anchor="w", pady=1)

tk.Label(tier3_minmax, text="Min", bg=FRAME_BG, fg=FG).pack(side="left")
tier3_min = tk.Entry(tier3_minmax, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG)
tier3_min.insert(0, str(settings.get("tier3_min", 0.55)))
tier3_min.pack(side="left", padx=5)

tk.Label(tier3_minmax, text="Max", bg=FRAME_BG, fg=FG).pack(side="left")
tier3_max = tk.Entry(tier3_minmax, width=6, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG)
tier3_max.insert(0, str(settings.get("tier3_max", 1.20)))
tier3_max.pack(side="left", padx=5)

#Update tier 3 number
def update_tier3_label(event=None):
    try:
        val = int(tier2_dist.get())
        tier3_info.config(text=f"Distance ≥ Tier 2 ({val})")
        settings["tier2_distance"] = val
        save_settings()
    except ValueError:
        pass

tier2_dist.bind("<KeyRelease>", update_tier3_label)


# -----------------------------
# CLICK TAB
# -----------------------------

# --- Offset Range ---
offset_label = tk.Label(click_tab, text="Offset Range (px):", bg=FRAME_BG, fg=FG)
offset_label.pack(pady=(5,0))

offset_entry = tk.Entry(click_tab, width=10,
                        bg=ENTRY_BG, fg=ENTRY_FG,
                        insertbackground=FG)
offset_entry.insert(0, str(settings["offset_range"]))
offset_entry.pack(pady=(0,5))

def update_offset(event=None):
    global OFFSET_RANGE
    try:
        value = int(offset_entry.get())
        settings["offset_range"] = value
        OFFSET_RANGE = value
        save_settings()
    except ValueError:
        pass

offset_entry.bind("<KeyRelease>", update_offset)


# --- Timing Jitter ---
jitter_label = tk.Label(click_tab, text="Timing Jitter (ms):", bg=FRAME_BG, fg=FG)
jitter_label.pack()

jitter_entry = tk.Entry(click_tab, width=10,
                        bg=ENTRY_BG, fg=ENTRY_FG,
                        insertbackground=FG)
jitter_entry.insert(0, str(settings["timing_jitter"]))
jitter_entry.pack(pady=(0,5))

def update_jitter(event=None):
    global TIMING_JITTER
    try:
        value = int(jitter_entry.get())
        settings["timing_jitter"] = value
        TIMING_JITTER = value
        save_settings()
    except ValueError:
        pass

jitter_entry.bind("<KeyRelease>", update_jitter)



root.mainloop()
