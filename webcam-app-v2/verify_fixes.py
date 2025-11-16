#!/usr/bin/env python3
"""
Verification Script - Check if GPU fixes are properly applied
Run this before starting the app to ensure everything is configured
"""

import os
import sys

def check_fix_applied(filepath, search_string):
    """Check if a fix was applied to a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return search_string in content
    except Exception as e:
        return False

def verify_all_fixes():
    """Verify all GPU fixes are applied"""
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║           🔍 GPU FIXES VERIFICATION SCRIPT                     ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    checks = [
        ("main.py", "TF_FORCE_GPU_ALLOW_GROWTH", "Main entry point GPU config"),
        ("app/services/face_recognition.py", "TF_XLA_FLAGS", "Face recognition GPU config"),
        ("app/services/multi_angle_capture.py", "XLA_FLAGS", "Multi-angle capture GPU config"),
        ("app/services/webcam_processor.py", "CUDA_HOME", "Webcam processor GPU config"),
    ]
    
    all_passed = True
    
    print("📋 Checking file modifications:\n")
    
    for filepath, search_string, description in checks:
        full_path = f"/home/husain/alrazy/webcam-app-v2/{filepath}"
        if check_fix_applied(full_path, search_string):
            print(f"  ✅ {filepath}")
            print(f"     └─ {description}")
        else:
            print(f"  ❌ {filepath}")
            print(f"     └─ {description} NOT FOUND")
            all_passed = False
    
    print("\n" + "="*70)
    
    tools = [
        "gpu_fix.py",
        "run_app.sh",
        "quickstart.sh",
        "GPU_FIXES.md",
        "INSTALLATION_COMPLETE.md",
        "README_GPU_FIXES.md"
    ]
    
    print("📦 Checking new tools and documentation:\n")
    
    for tool in tools:
        full_path = f"/home/husain/alrazy/webcam-app-v2/{tool}"
        if os.path.exists(full_path):
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} NOT FOUND")
            all_passed = False
    
    print("\n" + "="*70)
    print("⚙️  Environment Variable Check:\n")
    
    required_vars = [
        'TF_FORCE_GPU_ALLOW_GROWTH',
        'TF_XLA_FLAGS',
        'XLA_FLAGS',
        'CUDA_HOME'
    ]
    
    for var in required_vars:
        if var in os.environ:
            print(f"  ✅ {var} = {os.environ[var]}")
        else:
            print(f"  ℹ️  {var} not set (will be set at startup)")
    
    print("\n" + "="*70)
    print("📊 Status Summary:\n")
    
    if all_passed:
        print("  ✅ All GPU fixes successfully applied!")
        print("  ✅ All new tools and documentation created!")
        print("  ✅ Ready to start the application!\n")
        print("  Next step: bash run_app.sh")
        return 0
    else:
        print("  ⚠️  Some checks failed!")
        print("  ⚠️  Please ensure all files are in place!\n")
        return 1

if __name__ == '__main__':
    exit_code = verify_all_fixes()
    sys.exit(exit_code)
