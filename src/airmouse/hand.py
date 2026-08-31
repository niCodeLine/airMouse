"""Small, dependency-free geometry model for a tracked human hand.

This module represents the 21 landmarks returned by MediaPipe-style hand
tracking and provides a few simple geometric helpers used by the gesture layer.

There is intentionally no OpenCV, MediaPipe, webcam, or macOS dependency here.
The goal is to keep hand geometry easy to understand, deterministic, and easy
to test.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import IntEnum


class Landmark(IntEnum):
    """Canonical indices of the 21 hand landmarks.

    The values match MediaPipe's landmark ordering exactly, so we can use
    readable names such as `Landmark.INDEX_TIP` instead of raw indices like 8.
    """

    WRIST = 0

    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4

    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8

    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12

    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16

    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


@dataclass(frozen=True)
class Point:
    """A normalized 3D landmark reported by the hand tracker.

    Coordinates are normally normalized rather than expressed in pixels.

    Attributes:
        x: Horizontal position.
        y: Vertical position.
        z: Relative depth.
    """

    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: Point) -> float:
        """Return the Euclidean 3D distance to another point."""

        return math.dist(
            (self.x, self.y, self.z),
            (other.x, other.y, other.z),
        )


class HandLandmarks(Sequence[Point]):
    """Represent the 21 landmarks of a single tracked hand.

    The object behaves like a normal sequence, but landmarks can be accessed
    with the `Landmark` enum:

        hand[Landmark.INDEX_TIP]

    instead of relying on less readable raw indices:

        hand[8]

    This class also provides the basic geometry needed by the gesture
    interpreter, such as normalized distances and finger-extension checks.
    """

    LANDMARK_COUNT = 21

    def __init__(self, points: Iterable[Point]) -> None:
        self._points = tuple(points)

        if len(self._points) != self.LANDMARK_COUNT:
            raise ValueError(
                f"a hand must contain exactly {self.LANDMARK_COUNT} landmarks"
            )

    def __getitem__(self, index: int | slice) -> Point | Sequence[Point]:
        return self._points[index]

    def __len__(self) -> int:
        return len(self._points)

    def __iter__(self) -> Iterator[Point]:
        return iter(self._points)

    @property
    def palm_size(self) -> float:
        """Return a rough scale reference for the current hand.

        The wrist-to-middle-MCP distance is used as an approximation of hand
        size. Other distances can be divided by this value so gesture
        thresholds remain relatively stable when the hand moves closer to or
        farther from the camera.

        A tiny lower bound avoids division by zero if a malformed frame is
        received from the tracker.
        """

        wrist = self[Landmark.WRIST]
        middle_mcp = self[Landmark.MIDDLE_MCP]

        size = wrist.distance_to(middle_mcp)

        return max(size, 1e-6)

    def normalized_distance(
        self,
        first: Landmark,
        second: Landmark,
    ) -> float:
        """Return the distance between two landmarks relative to hand size.

        Raw landmark distances change when the hand moves toward or away from
        the webcam. Dividing by `palm_size` makes gesture thresholds much less
        dependent on camera distance.
        """

        distance = self[first].distance_to(self[second])

        return distance / self.palm_size

    def finger_extended(
        self,
        tip: Landmark,
        pip: Landmark,
        *,
        threshold: float = 1.15,
    ) -> bool:
        """Estimate whether a non-thumb finger is extended.

        For an extended finger, the fingertip should be noticeably farther
        from the wrist than its PIP joint.

        `threshold` adds a small margin so tiny tracking fluctuations do not
        constantly flip the result between extended and folded.
        """

        wrist = self[Landmark.WRIST]

        tip_distance = wrist.distance_to(self[tip])
        pip_distance = wrist.distance_to(self[pip])

        return tip_distance > pip_distance * threshold

    def thumb_extended(self, *, threshold: float = 1.15) -> bool:
        """Estimate whether the thumb is extended.

        The thumb moves differently from the other fingers, so using the same
        wrist-to-tip comparison is not very reliable.

        Instead, the pinky MCP is used as an anchor on the opposite side of
        the palm. When the thumb is extended, its tip should be farther from
        that anchor than the thumb's IP joint.
        """

        anchor = self[Landmark.PINKY_MCP]

        thumb_tip_distance = anchor.distance_to(
            self[Landmark.THUMB_TIP]
        )
        thumb_ip_distance = anchor.distance_to(
            self[Landmark.THUMB_IP]
        )

        return thumb_tip_distance > thumb_ip_distance * threshold