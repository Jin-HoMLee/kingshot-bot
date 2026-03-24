# kingshot-bot

Minimal end-to-end Python bot that detects when cooldowns end in the **KingShot Mac App** and automatically clicks the relevant buttons.

---

## How it works

1. `main.py` captures the full screen with **PyAutoGUI** once per monitoring interval.
2. **OpenCV** converts each frame to HSV colour space and thresholds for the red dots that indicate active cooldowns.
3. When the bot observes that *all* red dots disappear (cooldown → complete transition), it clicks every button listed in `config.json`.

---

## Requirements

| Requirement | Version |
|---|---|
| macOS | 12 Monterey or later |
| Python | 3.10 or later |

> **macOS accessibility permissions** — System Settings → Privacy & Security → Accessibility → add your Terminal (or IDE).  
> **Screen Recording permission** — System Settings → Privacy & Security → Screen Recording → add your Terminal (or IDE).  
> Both permissions are required for PyAutoGUI to capture the screen and move the mouse.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Jin-HoMLee/kingshot-bot.git
cd kingshot-bot

# 2. (Optional but recommended) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration (`config.json`)

```json
{
  "monitor_interval": 1.0,
  "buttons": [
    { "name": "collect_reward", "x": 760, "y": 480 },
    { "name": "confirm_dialog", "x": 760, "y": 540 }
  ],
  "red_dot": {
    "hsv_lower": [0,   150, 150],
    "hsv_upper": [10,  255, 255],
    "min_area":  20,
    "max_area":  500
  },
  "window_title": "KingShot"
}
```

| Key | Description |
|---|---|
| `monitor_interval` | Seconds between each screen capture |
| `buttons[].x` / `buttons[].y` | Screen coordinates to click |
| `red_dot.hsv_lower` / `hsv_upper` | HSV colour bounds for the red dot |
| `red_dot.min_area` / `max_area` | Blob size filter (pixels) |
| `window_title` | KingShot window title (reserved for future window-scoped capture) |

### Finding button coordinates

1. Open the KingShot Mac App.
2. Run the following one-liner to print the mouse position every second — move your cursor to the button you want to click and note the coordinates:

   ```bash
   python3 -c "import pyautogui, time; [print(pyautogui.position()) for _ in iter(lambda: time.sleep(1), None)]"
   ```

3. Update the `x` and `y` values in `config.json` for each button.

### Tuning red-dot detection

If the bot misses cooldown dots or produces false positives:

- **Increase `min_area`** to filter out tiny noise blobs.
- **Adjust `hsv_lower` / `hsv_upper`** to match the exact red shade used by KingShot.  
  You can inspect HSV values with:

  ```python
  import cv2, numpy as np, pyautogui
  img = np.array(pyautogui.screenshot())
  hsv = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2HSV)
  # Sample the pixel at the red dot location (row, col):
  print(hsv[480, 760])
  ```

---

## Running the bot

```bash
python main.py
```

Press **Ctrl+C** to stop.

### Example output

```
KingShot bot started. Press Ctrl+C to stop.
Monitoring every 1.0s | buttons: ['collect_reward', 'confirm_dialog']
[14:05:32] Red dot count changed: 0 → 2
[14:07:18] Cooldown(s) finished! Clicking buttons...
  Clicked 'collect_reward' at (760, 480)
  Clicked 'confirm_dialog' at (760, 540)
```

---

## Project structure

```
kingshot-bot/
├── main.py          # Bot engine
├── config.json      # Button coordinates & detection settings
├── requirements.txt # Python dependencies
└── README.md        # This file
```

---

## License

MIT — see [LICENSE](LICENSE).
