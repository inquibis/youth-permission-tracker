#!/usr/bin/env python
"""Quick test runner to check which tests pass/fail"""
import subprocess
import sys

def run_tests():
    """Run pytest and parse results"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         "tests/unit/api/", 
         "-v", 
         "--tb=no",
         "-q"],
        capture_output=True,
        text=True,
        cwd="c:\\sandbox\\youth-permission-tracker"
    )
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")

if __name__ == "__main__":
    run_tests()
