import pytest

from airmouse.hand import HandLandmarks, Landmark, Point


def make_hand():
    points = [Point(0.5, 0.8) for _ in range(21)]
    points[Landmark.MIDDLE_MCP] = Point(0.5, 0.6)
    points[Landmark.INDEX_PIP] = Point(0.4, 0.5)
    points[Landmark.INDEX_TIP] = Point(0.4, 0.2)
    return HandLandmarks(points)


def test_hand_requires_the_canonical_landmark_count():
    with pytest.raises(ValueError, match="21"):
        HandLandmarks([Point(0, 0)])


def test_distances_are_normalized_by_palm_size():
    hand = make_hand()

    assert hand.palm_size == pytest.approx(0.2)
    assert hand.normalized_distance(
        Landmark.INDEX_PIP, Landmark.INDEX_TIP
    ) == pytest.approx(1.5)
    assert hand.finger_extended(Landmark.INDEX_TIP, Landmark.INDEX_PIP)
