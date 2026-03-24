"""
KingShot Cooldown Bot
=====================
Connects to an iPhone via Appium, captures the KingShot game screen,
detects red cooldown-done indicators using OpenCV, and taps configured
buttons whenever a cooldown completes.

Usage:
    python main.py [--config config.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from io import BytesIO

import cv2
import numpy as np
from appium import webdriver
from appium.options import XCUITestOptions
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Load and return the JSON configuration file."""
    with open(path, "r") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Appium driver
# ---------------------------------------------------------------------------

def create_driver(cfg: dict) -> webdriver.Remote:
    """Create and return an Appium WebDriver connected to the iPhone."""
    appium_cfg = cfg["appium"]
    caps = appium_cfg["capabilities"]

    options = XCUITestOptions()
    options.platform_name = caps["platformName"]
    options.platform_version = caps["platformVersion"]
    options.device_name = caps["deviceName"]
    options.udid = caps["udid"]
    options.bundle_id = caps["bundleId"]
    options.automation_name = caps["automationName"]
    options.no_reset = caps.get("noReset", True)
    options.new_command_timeout = caps.get("newCommandTimeout", 600)

    url = f"http://{appium_cfg['host']}:{appium_cfg['port']}"
    log.info("Connecting to Appium at %s …", url)
    driver = webdriver.Remote(url, options=options)
    log.info("Connected. Session id: %s", driver.session_id)
    return driver


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

def capture_screenshot(driver: webdriver.Remote) -> np.ndarray:
    """
    Capture a screenshot from the device and return it as a BGR NumPy array
    suitable for OpenCV processing.
    """
    png_bytes = driver.get_screenshot_as_png()
    pil_image = Image.open(BytesIO(png_bytes)).convert("RGB")
    bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return bgr


# ---------------------------------------------------------------------------
# Red-dot detection
# ---------------------------------------------------------------------------

def detect_red_dots(image: np.ndarray, detection_cfg: dict) -> list[tuple[int, int, int]]:
    """
    Detect red circular dots in *image* using HSV colour thresholding and
    Hough circles.

    Returns a list of (x, y, radius) tuples for each dot found.
    """
    rd = detection_cfg["red_dot"]
    lower1 = np.array(rd["hsv_lower"], dtype=np.uint8)
    upper1 = np.array(rd["hsv_upper"], dtype=np.uint8)
    lower2 = np.array(rd["hsv_lower2"], dtype=np.uint8)
    upper2 = np.array(rd["hsv_upper2"], dtype=np.uint8)
    min_r = rd["min_radius"]
    max_r = rd["max_radius"]

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Red wraps around in HSV – combine both hue ranges.
    mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower1, upper1),
        cv2.inRange(hsv, lower2, upper2),
    )

    # Morphological cleanup to reduce noise.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    circles = cv2.HoughCircles(
        mask,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min_r * 2,
        param1=50,
        param2=15,
        minRadius=min_r,
        maxRadius=max_r,
    )

    if circles is None:
        return []

    return [
        (int(x), int(y), int(r))
        for x, y, r in np.round(circles[0]).astype(int)
    ]


# ---------------------------------------------------------------------------
# Button tap
# ---------------------------------------------------------------------------

def tap_button(driver: webdriver.Remote, button: dict) -> None:
    """Tap a screen coordinate defined in the configuration."""
    x, y = button["x"], button["y"]
    log.info("Tapping button '%s' at (%d, %d)", button["name"], x, y)
    driver.execute_script("mobile: tap", {"x": x, "y": y})


# ---------------------------------------------------------------------------
# Main bot loop
# ---------------------------------------------------------------------------

def run_bot(cfg: dict) -> None:
    """
    Main loop:
      1. Capture screenshot.
      2. Detect red dots.
      3. For each configured button whose cooldown was previously active (dots
         present) and is now done (no dots near its coordinate), tap it.
      4. Sleep for the configured interval.
    """
    driver = create_driver(cfg)
    buttons = cfg["buttons"]
    detection_cfg = cfg["detection"]
    interval = cfg.get("interval_seconds", 5)

    # Track whether a red dot was seen near each button on the *previous* tick.
    # None means we have not checked yet (first iteration).
    previous_dot_state: dict[str, bool | None] = {b["name"]: None for b in buttons}

    log.info("Bot started. Monitoring %d button(s). Press Ctrl+C to stop.", len(buttons))

    try:
        while True:
            image = capture_screenshot(driver)
            dots = detect_red_dots(image, detection_cfg)
            log.debug("Detected %d red dot(s): %s", len(dots), dots)

            for button in buttons:
                dot_near_button = _dot_near_coordinate(
                    dots, button["x"], button["y"], radius=50
                )

                prev = previous_dot_state[button["name"]]

                if prev is True and not dot_near_button:
                    # Cooldown just ended → tap the button.
                    tap_button(driver, button)
                elif prev is None and not dot_near_button:
                    # First check and no dot: nothing to do yet.
                    log.debug(
                        "Button '%s': no red dot on first check – waiting for cooldown.",
                        button["name"],
                    )
                elif dot_near_button:
                    log.debug("Button '%s': cooldown active (red dot visible).", button["name"])

                previous_dot_state[button["name"]] = dot_near_button

            time.sleep(interval)

    except KeyboardInterrupt:
        log.info("Interrupted by user – shutting down.")
    finally:
        driver.quit()
        log.info("Appium session closed.")


def _dot_near_coordinate(
    dots: list[tuple[int, int, int]], x: int, y: int, radius: int
) -> bool:
    """Return True if any detected dot centre is within *radius* pixels of (x, y)."""
    for dx, dy, _ in dots:
        if (dx - x) ** 2 + (dy - y) ** 2 <= radius ** 2:
            return True
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="KingShot cooldown bot")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the JSON configuration file (default: config.json)",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        log.error("Configuration file not found: %s", args.config)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in configuration file: %s", exc)
        sys.exit(1)

    run_bot(cfg)


if __name__ == "__main__":
    main()
