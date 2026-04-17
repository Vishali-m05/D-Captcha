# Camera Access Issues - Troubleshooting Guide

## Problem
```
Camera index out of range
Failed to open ANY camera (tried indices 0, 1, 2)
```

## Solutions

### If you're on **WSL (Windows Subsystem for Linux)**:

1. **Install usbipd on Windows (PowerShell as Admin)**:
```powershell
winget install usbipd
```

2. **Find your webcam device**:
```powershell
usbipd list
```
Look for your camera in the list (usually mentions "Camera" or "Webcam")

3. **Attach camera to WSL**:
```powershell
usbipd attach --wsl --busid <BUS-ID>
```
Replace `<BUS-ID>` with the one from step 2 (e.g., 1-5)

4. **Verify camera is now available**:
```bash
# In WSL terminal
ls /dev/video*
```

5. **In Windows PowerShell, before running the app**:
```powershell
cd e:\D-CAPTCHA_\D-CAPTCHA
python app.py
```

### If you're on **Native Windows**:

1. **Check Windows Device Manager**:
   - Right-click "This PC" → Manage → Device Manager
   - Look under "Imaging devices"
   - Your camera should be listed there

2. **Reinstall camera drivers**:
   - Right-click your camera → Update driver
   - Select "Search automatically for updated driver software"

3. **Check camera is not in use**:
   - Close other apps using the camera (Teams, Zoom, etc.)
   - Restart the system

4. **Run as Administrator**:
   - Open Command Prompt as Administrator
   - Run: `python app.py`

### If you're on **Linux (native)**:

1. **Check if camera is detected**:
```bash
ls -la /dev/video*
v4l2-ctl --list-devices
```

2. **Install v4l2-utils** (for testing):
```bash
sudo apt-get install v4l2-utils
```

3. **Test camera**:
```bash
ffplay /dev/video0
```

4. **Fix permissions** (if camera exists but not accessible):
```bash
sudo usermod -a -G video $USER
# Logout and login again for changes to take effect
```

## Quick Test

Run this Python command to test if OpenCV can access the camera:

```python
import cv2

# Test different indices
for idx in [0, 1, -1]:
    print(f"\nTrying index {idx}...")
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ SUCCESS: Camera found at index {idx}")
            print(f"   Resolution: {int(cap.get(3))}x{int(cap.get(4))}")
            cap.release()
            break
    cap.release()
else:
    print("\n❌ NO CAMERA FOUND")
```

## Temporary Workaround (Testing without camera)

If you need to run the app without a real camera temporarily:
1. Comment out the `monitoring_loop()` call in app.py
2. This will let you test the UI and other components

