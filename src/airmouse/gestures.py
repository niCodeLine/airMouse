"""Interpret hand landmarks and convert them into deliberate gestures.

This module contains the gesture-recognition logic of airMouse.

It does not know anything about webcams, OpenCV, PyAutoGUI, or macOS.
It simply receives a normalized representation of a hand and decides
what the user is trying to do.

Keeping this logic isolated makes gestures easier to understand, tweak,
and test without having to run the whole application.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .hand import HandLandmarks, Landmark, Point


class Gesture(str, Enum):
    """Gestures understood by airMouse."""

    MOVE = "move"
    DRAG = "drag"
    RIGHT_CLICK = "right_click"
    SCROLL = "scroll"
    VOLUME = "volume"
    BRIGHTNESS = "brightness"

    # Commands rather than continuous mouse actions.
    PAUSE = "pause"
    RESUME = "resume"
    QUIT = "quit"


@dataclass(frozen=True)
class GestureResult:
    """Result of interpreting one frame of hand landmarks.

    Attributes:
        gesture:
            Gesture detected in the current frame.

        cursor:
            Hand point used as the cursor reference.

        value:
            Optional extra value associated with the gesture.

            For example:
            - volume / brightness -> percentage from 0 to 100
            - scroll -> direction/intensity from -1 to 1
            - move / drag / commands -> None
    """

    gesture: Gesture
    cursor: Point
    value: float | None = None


class GestureInterpreter:
    """Translate hand geometry into airMouse gestures.

    Distances between landmarks are normalized by hand size, so gesture
    detection does not depend strongly on how close the hand is to the camera.

    `pinch_threshold` controls how close two normalized landmarks must be
    before they are considered to be touching.
    """

    def __init__(self, pinch_threshold: float = 0.32) -> None:
        if pinch_threshold <= 0:
            raise ValueError("pinch_threshold must be positive")

        self.pinch_threshold = pinch_threshold

    def _touches(self, hand: HandLandmarks, finger: Landmark) -> bool:
        """Return True when the thumb tip is touching a given fingertip.

        The distance is normalized by hand scale, so the same threshold works
        reasonably well whether the hand is near or far from the webcam.
        """

        distance = hand.normalized_distance(
            Landmark.THUMB_TIP,
            finger,
        )

        return distance <= self.pinch_threshold

    @staticmethod
    def _range_value(distance: float) -> float:
        """Convert thumb-to-index distance into a percentage from 0 to 100.

        This is used for continuous controls such as volume and brightness.

        Distances below `minimum` become 0%.
        Distances above `maximum` become 100%.
        Everything between them is mapped linearly.
        """

        minimum = 0.35
        maximum = 1.75

        value = (distance - minimum) * 100 / (maximum - minimum)

        # Clamp the result so small tracking errors cannot produce values
        # below 0 or above 100.
        return max(0.0, min(100.0, value))

    @staticmethod
    def _scroll_value(hand: HandLandmarks) -> float:
        """Estimate scroll direction and intensity from index-finger tilt.

        Returns a value between -1 and 1.

        The INDEX_MCP -> INDEX_PIP vector gives us the direction of the
        lower part of the index finger. Its angle is converted into a smooth
        scroll value instead of simply returning "up" or "down".
        """

        mcp = hand[Landmark.INDEX_MCP]
        pip = hand[Landmark.INDEX_PIP]

        dx = pip.x - mcp.x
        dy = pip.y - mcp.y

        angle = math.atan2(dy, dx)

        # Negated so the physical hand movement matches the desired
        # scrolling direction.
        value = -math.sin(angle)

        return max(-1.0, min(1.0, value))

    def interpret(self, hand: HandLandmarks) -> GestureResult:
        """Interpret one hand frame and return the most likely gesture.

        Gesture checks are intentionally ordered.

        More specific gestures such as Quit, Pause, Brightness, Drag, etc.
        must be checked before the generic MOVE fallback. Otherwise the same
        hand pose could accidentally be interpreted as a simpler gesture.
        """

        # --------------------------------------------------------------
        # Finger state
        # --------------------------------------------------------------
        # Determine which fingers are currently extended.
        #
        # For most fingers this is based on the tip relative to its PIP joint.
        # Thumb geometry is different, so HandLandmarks handles it separately.
        index = hand.finger_extended(
            Landmark.INDEX_TIP,
            Landmark.INDEX_PIP,
        )
        middle = hand.finger_extended(
            Landmark.MIDDLE_TIP,
            Landmark.MIDDLE_PIP,
        )
        ring = hand.finger_extended(
            Landmark.RING_TIP,
            Landmark.RING_PIP,
        )
        pinky = hand.finger_extended(
            Landmark.PINKY_TIP,
            Landmark.PINKY_PIP,
        )
        thumb = hand.thumb_extended()

        # Use the middle MCP (roughly around the palm) as the cursor anchor.
        #
        # A palm-based point tends to move more smoothly than a fingertip,
        # which naturally wiggles much more.
        cursor = hand[Landmark.MIDDLE_MCP]

        # Thumb-index distance is used as a continuous control for both
        # volume and brightness.
        thumb_index_distance = hand.normalized_distance(
            Landmark.THUMB_TIP,
            Landmark.INDEX_TIP,
        )

        thumb_touching_pinky = self._touches(
            hand,
            Landmark.PINKY_TIP,
        )

        # --------------------------------------------------------------
        # Command gestures
        # --------------------------------------------------------------

        # QUIT
        #
        # Index + middle + ring raised while thumb touches pinky.
        # A fairly unusual pose on purpose, since accidentally quitting
        # the application would be annoying.
        if index and middle and ring and thumb_touching_pinky:
            return GestureResult(
                gesture=Gesture.QUIT,
                cursor=cursor,
            )

        # PAUSE
        #
        # Closed fist: no fingers considered extended.
        if not any((thumb, index, middle, ring, pinky)):
            return GestureResult(
                gesture=Gesture.PAUSE,
                cursor=cursor,
            )

        # RESUME
        #
        # Peace sign: index + middle extended, ring + pinky down.
        if index and middle and not ring and not pinky:
            return GestureResult(
                gesture=Gesture.RESUME,
                cursor=cursor,
            )

        # --------------------------------------------------------------
        # Continuous controls
        # --------------------------------------------------------------

        # BRIGHTNESS
        #
        # Index + pinky raised.
        # Thumb-to-index distance controls brightness from 0 to 100.
        if thumb and index and pinky and not middle and not ring:
            brightness = self._range_value(thumb_index_distance)

            return GestureResult(
                gesture=Gesture.BRIGHTNESS,
                cursor=cursor,
                value=brightness,
            )

        # VOLUME
        #
        # Only the index finger is raised.
        # Thumb-to-index distance controls volume from 0 to 100.
        if index and not middle and not ring and not pinky:
            volume = self._range_value(thumb_index_distance)

            return GestureResult(
                gesture=Gesture.VOLUME,
                cursor=cursor,
                value=volume,
            )

        # --------------------------------------------------------------
        # Mouse actions
        # --------------------------------------------------------------

        # RIGHT CLICK
        #
        # Thumb touches ring finger while pinky stays raised.
        if self._touches(hand, Landmark.RING_TIP) and pinky:
            return GestureResult(
                gesture=Gesture.RIGHT_CLICK,
                cursor=cursor,
            )

        # DRAG
        #
        # Thumb touches middle finger while pinky stays raised.
        if self._touches(hand, Landmark.MIDDLE_TIP) and pinky:
            return GestureResult(
                gesture=Gesture.DRAG,
                cursor=cursor,
            )

        # SCROLL
        #
        # Thumb and index touch while the other three fingers remain raised.
        # The tilt of the index finger determines scroll direction/intensity.
        if (
            self._touches(hand, Landmark.INDEX_TIP)
            and middle
            and ring
            and pinky
        ):
            scroll = self._scroll_value(hand)

            return GestureResult(
                gesture=Gesture.SCROLL,
                cursor=cursor,
                value=scroll,
            )

        # --------------------------------------------------------------
        # Default behaviour
        # --------------------------------------------------------------
        # If no special gesture matches, simply use the hand to move
        # the cursor.
        return GestureResult(
            gesture=Gesture.MOVE,
            cursor=cursor,
        )