import pytest

from airmouse.control import CursorMapper, GestureHold
from airmouse.gestures import Gesture
from airmouse.hand import Point


def test_cursor_mapping_clamps_camera_edges_to_the_screen():
    mapper = CursorMapper(1000, 500, margin=0.1, smoothing=1)

    assert mapper.map(Point(0, 0)) == (0, 0)
    assert mapper.map(Point(1, 1)) == (1000, 500)


def test_cursor_mapping_smooths_abrupt_movements():
    mapper = CursorMapper(100, 100, margin=0, smoothing=0.25)

    assert mapper.map(Point(0, 0)) == (0, 0)
    assert mapper.map(Point(1, 1)) == pytest.approx((25, 25))


def test_gesture_hold_emits_once_until_the_gesture_changes():
    hold = GestureHold(frames=2)

    assert hold.update(Gesture.PAUSE) is False
    assert hold.update(Gesture.PAUSE) is True
    assert hold.update(Gesture.PAUSE) is False
    assert hold.update(Gesture.MOVE) is False
    assert hold.update(Gesture.PAUSE) is False
    assert hold.update(Gesture.PAUSE) is True
