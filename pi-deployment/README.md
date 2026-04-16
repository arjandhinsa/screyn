# Screyn on Raspberry Pi — Sentinel Mode

This guide sets up Screyn on a Raspberry Pi + Camera Module as a dedicated desk sentinel. The Pi runs the backend and CV pipeline; your laptop connects to its dashboard over the local network.

## Hardware

- **Raspberry Pi 4 (4GB+) or Pi 5** — Pi Zero 2 W works but is tight on memory
- **Raspberry Pi Camera Module v2 or v3** — v3 has better low-light performance
- **MicroSD card** 32GB+ (Class 10 / U3)
- **Monitor mount or tripod** for camera placement
- **Power supply** — official PSU recommended

## OS Setup

1. Flash **Raspberry Pi OS (64-bit, Bookworm) Lite** onto your SD card using Raspberry Pi Imager. Pre-configure:
   - Hostname: `screyn`
   - Username: your choice
   - WiFi credentials
   - Enable SSH
2. Boot the Pi and SSH in:
   ```
   ssh user@screyn.local
   ```
3. Update:
   ```
   sudo apt update && sudo apt upgrade -y
   ```

## Camera Setup

The Pi Camera Module uses `libcamera` / `picamera2` rather than OpenCV's `VideoCapture`. Install:

```
sudo apt install -y python3-picamera2 python3-opencv libatlas-base-dev
```

Test the camera:
```
libcamera-hello --timeout 2000
```
You should see a preview window (or exit cleanly if no display attached).

## Install Screyn

```
git clone <your-repo-url> screyn
cd screyn/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install picamera2
```

**Note**: MediaPipe on the Pi can be slow to install. If `pip install mediapipe` fails, try:
```
pip install mediapipe --index-url=https://www.piwheels.org/simple
```

## Run It

Create a `.env` file:
```
cp .env.example .env
nano .env
```

Set:
```
SHOW_PREVIEW=false
CAMERA_INDEX=0
TARGET_FPS=10
```

(Pi 4 handles ~10 FPS comfortably; Pi 5 can push 15.)

Start the backend:
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

From your laptop, visit `http://screyn.local:8000/docs` to confirm it's running.

## Swap in picamera2 (if needed)

If you want to use `picamera2` directly instead of OpenCV's `VideoCapture`, replace the capture loop in `backend/app/services/camera.py`. A drop-in replacement using picamera2 would look roughly like:

```python
from picamera2 import Picamera2
picam = Picamera2()
picam.configure(picam.create_video_configuration(main={"size": (640, 480)}))
picam.start()

# In the capture loop:
frame = picam.capture_array()  # RGB array
frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
```

Left as a TODO — test OpenCV's VideoCapture first, it works with the Camera Module on Bookworm via libcamera shim.

## Run on Boot (systemd)

Create `/etc/systemd/system/screyn.service`:

```ini
[Unit]
Description=Screyn backend
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/screyn/backend
Environment="PATH=/home/<your-user>/screyn/backend/venv/bin"
ExecStart=/home/<your-user>/screyn/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:
```
sudo systemctl daemon-reload
sudo systemctl enable screyn
sudo systemctl start screyn
```

## Frontend

Two options:

**Option A (simplest)**: Run the frontend on your laptop and point it at the Pi. In `frontend/vite.config.js`, change the proxy target to `http://screyn.local:8000`.

**Option B**: Build the frontend and serve it from the Pi.
```
cd ../frontend
npm install
npm run build
# Then serve dist/ via nginx or Caddy on the Pi
```

## Placement Tips

- Put the Pi camera **on top of your monitor, centred**, pointed at face height
- Aim for ~60cm between you and the camera
- Avoid strong backlighting (windows behind you) — wrecks exposure
- The Camera Module has a short ribbon cable; use the longer flex cable if your Pi is hidden away

## Future Additions

- Add a **BH1750 ambient light sensor** (I²C) to track room lux — correlates with eye strain
- Add a **DHT22** for temperature/humidity — low humidity = dry eyes
- Wire up a small **NeoPixel strip** for ambient focus indicator (glows green when focused, amber when overdue for a break)
