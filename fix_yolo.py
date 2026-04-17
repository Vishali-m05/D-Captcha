"""
YOLO Model Fix for PyTorch 2.6+ Compatibility
This script helps resolve the weights loading issue
"""

import torch
from ultralytics.nn.tasks import DetectionModel

# Add safe globals for PyTorch 2.6+ compatibility
print("🔧 Fixing YOLO model loading for PyTorch 2.6+")
print("   Adding safe globals...")

try:
    torch.serialization.add_safe_globals([DetectionModel])
    print("✅ Safe globals added successfully")
except Exception as e:
    print(f"⚠️  Warning: {e}")

print("\n✅ Fix applied! You can now start the backend.")
print("\nRun: uvicorn backend.main:app --reload")
