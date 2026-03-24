# kingshot-bot

A minimal Python bot that connects to an iPhone running **KingShot** via Appium,
detects when cooldown indicators (red dots) disappear, and automatically taps
the relevant buttons.

---

## How It Works

```
iPhone (KingShot running)
        │  USB
        ▼
  Appium Server (Mac)
        │  HTTP
        ▼
  main.py (Python bot)
    ├─ captures screenshot
    ├─ detects red dots with OpenCV
    ├─ tracks cooldown state per button
    └─ taps button when cooldown ends
```

1. The bot takes a screenshot of the game every `interval_seconds` seconds.
2. It looks for **red circular dots** near each configured button coordinate.
3. When a red dot was visible on the previous tick and is **gone** on the
   current tick, the bot taps that button — the cooldown just ended.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.11 | `brew install python` |
| Node.js | ≥ 18 | `brew install node` |
| Appium | ≥ 2.x | `npm install -g appium` |
| Appium XCUITest driver | latest | `appium driver install xcuitest` |
| Xcode | latest | Mac App Store |
| Xcode Command Line Tools | latest | `xcode-select --install` |

Your iPhone must be **trusted** by your Mac (tap *Trust* on the device when
prompted) and **developer mode** must be enabled
(*Settings → Privacy & Security → Developer Mode*).

---

## Setup

### 1 — Clone and install Python dependencies

```bash
git clone https://github.com/Jin-HoMLee/kingshot-bot.git
cd kingshot-bot
pip install -r requirements.txt
```

### 2 — Find your device UDID

Connect the iPhone via USB, then run:

```bash
# With Xcode tools
xcrun xctrace list devices

# Or with libimobiledevice (brew install libimobiledevice)
idevice_id -l
```

Copy the UDID string — you will need it in `config.json`.

### 3 — Find the KingShot bundle ID

```bash
# While the app is open on the device:
ideviceinstaller -l | grep -i king
```

Typical output: `com.yourcompany.kingshot`

### 4 — Configure the bot

Edit **`config.json`**:

```json
{
  "appium": {
    "host": "127.0.0.1",
    "port": 4723,
    "capabilities": {
      "platformVersion": "17.0",       ← match your iOS version
      "udid": "YOUR_DEVICE_UDID",      ← from step 2
      "bundleId": "com.…kingshot",     ← from step 3
      ...
    }
  },
  "buttons": [
    { "name": "collect_resources", "x": 100, "y": 200 },
    { "name": "start_training",    "x": 300, "y": 400 }
  ],
  ...
}
```

#### Finding button coordinates

The easiest way is to use **Appium Inspector**
(`npm install -g appium-inspector` or download the desktop app) — tap any
element to see its x/y coordinates.

Alternatively, take a screenshot and open it in Preview:
*Tools → Show Inspector* shows pixel coordinates as you move the mouse.

#### Tuning red-dot detection

The `detection.red_dot` section controls the HSV colour ranges used to find
red pixels.  If dots are being missed or there are false positives, adjust:

| Key | Meaning |
|-----|---------|
| `hsv_lower` / `hsv_upper` | Lower hue range for red (0–10°) |
| `hsv_lower2` / `hsv_upper2` | Upper hue range for red (170–180°) |
| `min_radius` / `max_radius` | Expected dot size in pixels |

You can test your thresholds interactively:

```python
import cv2, numpy as np
img = cv2.imread("screenshot.png")
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, np.array([0,150,150]), np.array([10,255,255]))
cv2.imshow("mask", mask); cv2.waitKey(0)
```

---

## Running the Bot

### Terminal 1 — Start the Appium server

```bash
appium
```

You should see `Appium REST http interface listener started on 0.0.0.0:4723`.

### Terminal 2 — Start the bot

```bash
python main.py
# or specify a different config file:
python main.py --config my_config.json
```

Stop the bot any time with **Ctrl+C**.

---

## Project Structure

```
kingshot-bot/
├── main.py          # Bot engine
├── config.json      # All settings (edit this before running)
├── requirements.txt # Python dependencies
└── README.md        # This file
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Could not start a new session` | Make sure Appium is running and the UDID/bundleId are correct |
| Bot connects but no taps happen | Verify button coordinates with Appium Inspector |
| Red dots not detected | Tune HSV thresholds; save a screenshot and test manually |
| `WebDriverException: timeout` | Increase `newCommandTimeout` in `config.json` |
| iPhone not recognised by Mac | Re-trust device: disconnect → reconnect → tap *Trust* on iPhone |

---

## Dependencies

- [appium-python-client](https://pypi.org/project/Appium-Python-Client/) — Appium WebDriver for Python
- [opencv-python](https://pypi.org/project/opencv-python/) — Image processing and red-dot detection
- [Pillow](https://pypi.org/project/Pillow/) — PNG screenshot decoding
- [numpy](https://pypi.org/project/numpy/) — Array operations used by OpenCV

---

## License

MIT — see [LICENSE](LICENSE).