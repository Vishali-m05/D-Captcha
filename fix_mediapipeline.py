import sys
import os
import importlib

def diagnose_mediapipe():
    print("🔍 Diagnosing MediaPipe Installation...")
    
    # Check for shadowing
    cwd = os.getcwd()
    shadowing_file = os.path.join(cwd, "mediapipe.py")
    if os.path.exists(shadowing_file):
        print(f"❌ CRITICAL ERROR: Found 'mediapipe.py' in current directory: {shadowing_file}")
        print("   This file shadows the real library. Please rename or delete it.")
        return

    try:
        import mediapipe
        print(f"✅ MediaPipe imported from: {os.path.dirname(mediapipe._file_)}")
        
        if hasattr(mediapipe, "solutions"):
            print("✅ mediapipe.solutions is available!")
        else:
            print("❌ mediapipe.solutions is MISSING!")
            print(f"   Available attributes: {dir(mediapipe)[:20]}...")
            
            # Try explicit import
            try:
                import mediapipe.python.solutions
                print("⚠️  Fixed by explicit import: import mediapipe.python.solutions")
            except ImportError as e:
                print(f"❌ Explicit import failed: {e}")

    except ImportError as e:
        print(f"❌ Failed to import mediapipe: {e}")

    print("\n📦 Reinstalling MediaPipe (Fix)...")
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "mediapipe"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mediapipe==0.10.8"])
        print("✅ MediaPipe reinstalled successfully. Please try running the app again.")
    except Exception as e:
        print(f"❌ Reinstall failed: {e}")

if __name__ == "_main_":
    diagnose_mediapipe()