"""State helpers for stable cursor and gesture control.

This module contains the small pieces of state that sit between raw gesture
recognition and the desktop actions performed by airMouse.

There are two main responsibilities here:

- map normalized camera coordinates onto the screen while smoothing movement
- require command gestures to remain stable for several frames before firing

Keeping this state separate from gesture recognition makes both parts easier to
reason about and test.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gestures import Gesture
from .hand import Point


@dataclass
class CursorMapper:
    """Map normalized camera coordinates to screen coordinates.

    The hand tracker reports positions in normalized camera space, usually in
    the range 0.0 to 1.0.

    This class:

    1. removes a margin around the camera frame
    2. clamps the remaining position to the usable area
    3. scales it to the screen dimensions
    4. smooths movement using the previous cursor position

    The margin means you do not need to physically move your hand all the way
    to the edge of the webcam image to reach the edge of the screen.
    """

    width: int
    height: int

    # Fraction of the camera frame ignored on each side.
    # 0.14 means roughly 14% is trimmed from every edge.
    margin: float = 0.14

    # Interpolation factor between the previous and target position.
    #
    # Lower values = smoother but slower cursor.
    # Higher values = faster but more sensitive cursor.
    smoothing: float = 0.35

    _previous: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        """Validate mapper configuration after dataclass initialization."""

        if self.width <= 0 or self.height <= 0:
            raise ValueError("screen dimensions must be positive")

        if not 0 <= self.margin < 0.5:
            raise ValueError("margin must be between 0 and 0.5")

        if not 0 < self.smoothing <= 1:
            raise ValueError("smoothing must be between 0 and 1")

    def map(self, point: Point) -> tuple[float, float]:
        """Convert one normalized hand point into a smoothed screen position.

        Coordinates inside the configured margin are remapped to the full
        screen. Values outside that usable region are clamped, so the resulting
        cursor position always remains inside the screen.

        Returns:
            A `(x, y)` position in screen coordinates.
        """

        # Usable fraction of the camera image after removing both margins.
        span = 1 - 2 * self.margin

        # Move the usable camera region back into the 0..1 range.
        normalized_x = (point.x - self.margin) / span
        normalized_y = (point.y - self.margin) / span

        # Clamp positions outside the active region.
        normalized_x = max(0.0, min(1.0, normalized_x))
        normalized_y = max(0.0, min(1.0, normalized_y))

        # Convert normalized camera coordinates into screen coordinates.
        target_x = normalized_x * self.width
        target_y = normalized_y * self.height
        target = (target_x, target_y)

        # The first frame has nothing to smooth against.
        if self._previous is None:
            result = target

        else:
            previous_x, previous_y = self._previous

            # Linear interpolation:
            #
            # result = previous + (target - previous) * smoothing
            #
            # This prevents tiny landmark fluctuations from making the cursor
            # visibly shake around the screen.
            result = (
                previous_x + (target_x - previous_x) * self.smoothing,
                previous_y + (target_y - previous_y) * self.smoothing,
            )

        self._previous = result

        return result


class GestureHold:
    """Require a gesture to remain stable before emitting it.

    Some gestures should not trigger immediately when they appear in a single
    frame. Tracking noise, transitions between poses, or simply moving the hand
    can briefly resemble commands such as PAUSE or QUIT.

    `GestureHold` acts as a small temporal filter.

    A gesture must remain unchanged for `frames` consecutive updates before
    `update()` returns True.

    Once emitted, that same gesture will not emit again until the detected
    gesture changes first.
    """

    def __init__(self, frames: int = 10) -> None:
        if frames < 1:
            raise ValueError("frames must be at least one")

        self.frames = frames

        # Gesture currently being tracked.
        self._gesture: Gesture | None = None

        # Number of consecutive frames containing that gesture.
        self._count = 0

        # Prevent repeated emission while the user keeps holding the gesture.
        self._emitted = False

    def update(self, gesture: Gesture) -> bool:
        """Process one frame and report whether the gesture should fire.

        Returns True exactly once when the same gesture has been observed for
        at least `frames` consecutive updates.

        Example with `frames=3`:

            MOVE   -> False
            PAUSE  -> False
            PAUSE  -> False
            PAUSE  -> True
            PAUSE  -> False
            PAUSE  -> False
            MOVE   -> False

        The gesture must change before PAUSE can be emitted again.
        """

        # A new gesture starts a new stability count.
        if gesture != self._gesture:
            self._gesture = gesture
            self._count = 1
            self._emitted = False

        else:
            self._count += 1

        # Fire once after the gesture has remained stable for long enough.
        if self._count >= self.frames and not self._emitted:
            self._emitted = True
            return True

        return False