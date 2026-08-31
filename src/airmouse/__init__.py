"""Core gesture interpretation for airMouse."""

from .gestures import Gesture, GestureInterpreter, GestureResult
from .hand import HandLandmarks, Landmark, Point

__all__ = [
    "Gesture",
    "GestureInterpreter",
    "GestureResult",
    "HandLandmarks",
    "Landmark",
    "Point",
]
__version__ = "2.0.0"
