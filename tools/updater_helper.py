#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updater helper script
Used by application to reliably replace a running exe with a new file and restart it.
This script waits for the specified pid to exit (if provided), then moves the new file to the destination, starts it and exits.
If no pid is provided, falls back to waiting for the old file to be unlocked (poll-and-move).
"""

import argparse
import os
import sys
import time
import shutil
import subprocess
import ctypes


def wait_for_pid(pid: int):
    """Wait for process with PID to exit using Windows API"""
    # SYNCHRONIZE access right is 0x00100000
    SYNCHRONIZE = 0x00100000
    PROCESS_QUERY_INFORMATION = 0x0400
    # OpenProcess for the PID
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, int(pid))
    if not handle:
        # maybe process not found
        return
    # WAIT_INFINITE = 0xFFFFFFFF
    WAIT_INFINITE = 0xFFFFFFFF
    kernel32.WaitForSingleObject(handle, WAIT_INFINITE)
    kernel32.CloseHandle(handle)


def wait_for_file_unlock(path: str):
    """Wait until the file can be replaced (no longer opened by another process)."""
    # Try to open in exclusive mode by renaming to a temp name
    for i in range(60):  # wait up to 60s
        try:
            # Try to rename the file to itself (no-op) as a quick lock check
            if os.path.exists(path):
                tmp = path + '.locktest'
                os.replace(path, tmp)
                os.replace(tmp, path)
            return
        except Exception:
            time.sleep(1)
    # Give up


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, default=None, help='PID to wait for')
    parser.add_argument('--new', required=True, help='New file path')
    parser.add_argument('--dst', required=True, help='Destination path')
    args = parser.parse_args()

    new = os.path.abspath(args.new)
    dst = os.path.abspath(args.dst)

    try:
        if args.pid:
            wait_for_pid(args.pid)
        else:
            # fallback: wait for file unlock
            wait_for_file_unlock(dst)

        # Move new into place
        for attempt in range(10):
            try:
                # Replace (atomic if same filesystem)
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(new, dst)
                break
            except Exception as e:
                time.sleep(1)
        # Start the new exe
        try:
            subprocess.Popen([dst])
        except Exception:
            pass

    except Exception as e:
        # Last resort: if we couldn't complete, print error and exit
        print(f"Updater helper error: {e}")


if __name__ == '__main__':
    main()
