"""
kingshot-bot: Automatic cooldown detector and clicker for the KingShot Mac App.

Usage:
    python main.py

The bot continuously captures the KingShot window, detects red cooldown-done
indicators using OpenCV, and clicks the configured buttons whenever a cooldown
transitions from active to complete.
"""

import json
import time
import sys
from pathlib import Path

import cv2
import numpy as np
import pyautogui

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(path: Path) -> dict:
    """Load and return the JSON configuration file."""
    if not path.exists():
        sys.exit(
            f"[ERROR] Configuration file not found: {path}\n"
            "Please ensure config.json exists in the same directory as main.py."
        )
    with open(path, "r") as fh:
        return json.load(fh)


def capture_screenshot() -> np.ndarray:
    """Capture the full screen and return it as a BGR NumPy array."""
    screenshot = pyautogui.screenshot()
    frame = np.array(screenshot)
    # PyAutoGUI returns RGB; convert to BGR for OpenCV
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def detect_red_dots(frame: np.ndarray, cfg: dict) -> list[dict]:
    """
    Detect red dot indicators in *frame* using the HSV thresholds from *cfg*.

    Returns a list of dicts, each with keys ``x``, ``y``, and ``area``,
    representing the centroid and pixel area of every detected red blob.

    Red hues wrap around 180° in OpenCV HSV, so two ranges are checked:
    the primary range supplied in config.json and a mirror range that covers
    the upper hue band (170–180).
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower = np.array(cfg["red_dot"]["hsv_lower"], dtype=np.uint8)
    upper = np.array(cfg["red_dot"]["hsv_upper"], dtype=np.uint8)

    mask1 = cv2.inRange(hsv, lower, upper)

    # Mirror range for the high-hue red band (170-180)
    lower2 = np.array([170, lower[1], lower[2]], dtype=np.uint8)
    upper2 = np.array([180, upper[1], upper[2]], dtype=np.uint8)
    mask2 = cv2.inRange(hsv, lower2, upper2)

    mask = cv2.bitwise_or(mask1, mask2)

    # Remove noise with morphological opening
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = cfg["red_dot"]["min_area"]
    max_area = cfg["red_dot"]["max_area"]

    dots = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area <= area <= max_area:
            m = cv2.moments(contour)
            if m["m00"] > 0:
                cx = int(m["m10"] / m["m00"])
                cy = int(m["m01"] / m["m00"])
                dots.append({"x": cx, "y": cy, "area": area})

    return dots


def click_buttons(buttons: list[dict]) -> None:
    """Click each button defined in the configuration."""
    for btn in buttons:
        pyautogui.click(btn["x"], btn["y"])
        print(f"  Clicked '{btn['name']}' at ({btn['x']}, {btn['y']})")
        # Small pause between clicks so the UI has time to respond
        time.sleep(0.3)


def run(config: dict) -> None:
    """
    Main bot loop.

    Continuously captures the screen, checks for red cooldown dots, and
    clicks the configured buttons whenever a cooldown completes (i.e. a dot
    disappears after having been present).
    """
    interval = config.get("monitor_interval", 1.0)
    buttons = config.get("buttons", [])

    print("KingShot bot started. Press Ctrl+C to stop.")
    print(f"Monitoring every {interval}s | buttons: {[b['name'] for b in buttons]}")

    prev_dot_count = 0

    while True:
        try:
            frame = capture_screenshot()
            dots = detect_red_dots(frame, config)
            current_dot_count = len(dots)

            if prev_dot_count > 0 and current_dot_count == 0:
                # All dots have disappeared — cooldowns are complete
                print(f"[{time.strftime('%H:%M:%S')}] Cooldown(s) finished! Clicking buttons...")
                click_buttons(buttons)
            elif current_dot_count != prev_dot_count:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Red dot count changed: "
                    f"{prev_dot_count} → {current_dot_count}"
                )

            prev_dot_count = current_dot_count
            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nBot stopped.")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {type(exc).__name__}: {exc}. Retrying...")
            time.sleep(interval)


def main() -> None:
    config = load_config(CONFIG_PATH)
    run(config)


if __name__ == "__main__":
    main()
