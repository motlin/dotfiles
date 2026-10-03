#!/usr/bin/env python3
"""Resize the pointer immediately.

Usage: set-cursor-scale.py <scale>

The saved pointer size applies only at login; private CGSSetCursorScale applies it now.
"""
import ctypes
import sys

APPLICATION_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"


def main(scale):
    core_graphics = ctypes.cdll.LoadLibrary(APPLICATION_SERVICES)
    core_graphics.CGSMainConnectionID.restype = ctypes.c_int
    core_graphics.CGSSetCursorScale.argtypes = [ctypes.c_int, ctypes.c_float]
    core_graphics.CGSSetCursorScale.restype = ctypes.c_int
    return core_graphics.CGSSetCursorScale(core_graphics.CGSMainConnectionID(), scale)


if __name__ == "__main__":
    sys.exit(main(float(sys.argv[1])))
