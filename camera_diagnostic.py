#!/usr/bin/env python3
"""
Camera Diagnostic Tool for D-CAPTCHA
Tests camera availability and OpenCV configuration
"""

import cv2
import sys
import platform

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_info(text):
    print(f"ℹ️  {text}")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def check_system_info():
    print_header("SYSTEM INFORMATION")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"OpenCV Version: {cv2.__version__}")
    print(f"OpenCV Build Info:")
    print(f"  - Build Type: {cv2.getBuildInformation().split(chr(10))[0]}")

def check_camera_indices():
    print_header("SCANNING FOR CAMERAS")
    cameras_found = []
    
    for idx in range(-1, 10):  # Check indices -1 to 9
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    cameras_found.append(idx)
                    print_success(f"Camera found at index {idx}")
            else:
                if idx < 3:  # Only show detailed output for common indices
                    print_warning(f"Camera index {idx}: Device exists but cannot open")
        except Exception as e:
            pass
    
    if not cameras_found:
        print_error("NO CAMERAS FOUND")
        return False
    
    return True

def test_camera_backends():
    print_header("TESTING OPENCV BACKENDS")
    
    backends = [
        (cv2.CAP_DSHOW, "DirectShow (Windows)"),
        (cv2.CAP_MSMF, "Media Foundation (Windows)"),
        (cv2.CAP_V4L2, "V4L2 (Linux)"),
        (cv2.CAP_AUTO, "Auto-detect"),
    ]
    
    for backend_id, backend_name in backends:
        print(f"\nTesting: {backend_name}")
        try:
            cap = cv2.VideoCapture(0, backend_id)  # Try index 0
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    print_success(f"  {backend_name} works!")
                    print_info(f"  Resolution: {width}x{height} @ {fps:.1f} FPS")
                else:
                    print_warning(f"  {backend_name}: Opened but cannot read frames")
            else:
                print_warning(f"  {backend_name}: Cannot open camera")
            cap.release()
        except Exception as e:
            print_error(f"  {backend_name}: {e}")

def check_wsl_environment():
    print_header("WSL-SPECIFIC CHECKS")
    
    system_os = platform.system()
    if system_os != "Linux":
        print_info(f"Running on {system_os}, not Linux (not WSL)")
        return
    
    # Check if running in WSL
    try:
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                print_warning("WSL environment detected!")
                print("\n🔧 FIXES FOR WSL:")
                print("1. Use usbipd to attach your camera (Windows PowerShell - Admin):")
                print("   - Run: usbipd list")
                print("   - Find your camera's BUS-ID")
                print("   - Run: usbipd attach --wsl --busid <BUS-ID>")
                print("\n2. Then verify in WSL:")
                print("   - Run: ls /dev/video*")
                return
    except:
        pass
    
    # Regular Linux checks
    import os
    print_info("Checking for video devices...")
    if os.path.exists("/dev/video0"):
        print_success("Found /dev/video0")
    else:
        print_error("No /dev/video0 found")
        print_warning("Try: v4l2-ctl --list-devices")

def recommend_fixes():
    print_header("RECOMMENDED SOLUTIONS")
    
    system_os = platform.system()
    
    if system_os == "Windows":
        print("1. Check Windows Device Manager:")
        print("   - Right-click 'This PC' → Manage → Device Manager")
        print("   - Look under 'Imaging devices' for your camera")
        print("")
        print("2. Close other apps using camera:")
        print("   - Close Teams, Zoom, or other video apps")
        print("")
        print("3. Reinstall camera drivers:")
        print("   - Right-click camera → Update driver")
        print("")
        print("4. Try running as Administrator")
        
    elif system_os == "Linux":
        print("1. Check for V4L2 devices:")
        print("   - Run: v4l2-ctl --list-devices")
        print("")
        print("2. Test camera access:")
        print("   - Run: ffplay /dev/video0")
        print("")
        print("3. Fix device permissions:")
        print("   - Run: sudo usermod -a -G video $USER")
        print("   - Logout and login again")

def main():
    print("\n")
    print_header("D-CAPTCHA CAMERA DIAGNOSTIC TOOL")
    
    try:
        check_system_info()
        check_wsl_environment()
        
        if check_camera_indices():
            test_camera_backends()
            print_success("\n🎉 Camera appears to be working!")
        else:
            print_error("\n📹 No cameras detected. Checking for solutions...")
            recommend_fixes()
        
    except Exception as e:
        print_error(f"Diagnostic error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
