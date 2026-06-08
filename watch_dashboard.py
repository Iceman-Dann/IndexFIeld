#!/usr/bin/env python3
"""
IndexField Dashboard Watcher
Automatically compiles dashboard_standalone.html whenever dashboard.html
or any fragment inside dashboard-pages/ is edited.
"""

import os
import time
import sys
from compile_dashboard import compile_dashboard

pages_dir = "dashboard-pages"
source_file = "dashboard.html"

def get_mtimes():
    mtimes = {}
    if os.path.exists(source_file):
        mtimes[source_file] = os.path.getmtime(source_file)
    if os.path.exists(pages_dir):
        for filename in os.listdir(pages_dir):
            filepath = os.path.join(pages_dir, filename)
            if os.path.isfile(filepath):
                mtimes[filepath] = os.path.getmtime(filepath)
    return mtimes

def main():
    print("=" * 60)
    print("         IndexField Dashboard Auto-Compiler Watcher")
    print("=" * 60)
    print(f"Monitoring: '{source_file}' and '{pages_dir}/'")
    print("Will automatically rebuild 'dashboard_standalone.html' on change.")
    print("Press Ctrl+C to stop.\n")

    # Initial compile
    try:
        compile_dashboard()
    except Exception as e:
        print(f"[ERROR] Initial compilation failed: {e}")

    last_modified = get_mtimes()

    try:
        while True:
            time.sleep(1)
            current_mtimes = get_mtimes()
            changed = False
            
            # Check for changes or new files
            for path, mtime in current_mtimes.items():
                if path not in last_modified or mtime > last_modified[path]:
                    print(f"[DETECTED] File modified: {os.path.basename(path)}")
                    changed = True
                    
            # Check for deleted files
            for path in list(last_modified.keys()):
                if path not in current_mtimes:
                    print(f"[DETECTED] File deleted: {os.path.basename(path)}")
                    changed = True

            if changed:
                last_modified = current_mtimes
                print("Rebuilding dashboard_standalone.html...")
                try:
                    compile_dashboard()
                    print("[SUCCESS] Rebuilt complete!\n")
                except Exception as e:
                    print(f"[ERROR] Rebuild failed: {e}\n")
                    
    except KeyboardInterrupt:
        print("\n[OK] Watcher stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
