from airmouse import (
    Gesture,
    GestureInterpreter,
    HandLandmarks,
    Landmark,
    Point,
)

FINGERS = [
    (Landmark.INDEX_PIP, Landmark.INDEX_TIP, 0.36),
    (Landmark.MIDDLE_PIP, Landmark.MIDDLE_TIP, 0.46),
    (Landmark.RING_PIP, Landmark.RING_TIP, 0.56),
    (Landmark.PINKY_PIP, Landmark.PINKY_TIP, 0.66),
]


def pose(*, extended=(), thumb=False, touches=None):
    points = [Point(0.5, 0.72) for _ in range(21)]
    points[Landmark.WRIST] = Point(0.5, 0.9)
    points[Landmark.MIDDLE_MCP] = Point(0.5, 0.7)
    points[Landmark.PINKY_MCP] = Point(0.68, 0.72)
    points[Landmark.THUMB_IP] = Point(0.63, 0.72)
    points[Landmark.THUMB_TIP] = Point(0.64 if not thumb else 0.3, 0.72)
    for pip, tip, x in FINGERS:
        points[pip] = Point(x, 0.66)
        points[tip] = Point(x, 0.35 if tip in extended else 0.73)
    if touches is not None:
        points[Landmark.THUMB_TIP] = points[touches]
    return HandLandmarks(points)


def test_open_motion_defaults_to_cursor_movement():
    hand = pose(
        extended={
            Landmark.INDEX_TIP,
            Landmark.MIDDLE_TIP,
            Landmark.RING_TIP,
            Landmark.PINKY_TIP,
        },
        thumb=True,
    )

    assert GestureInterpreter().interpret(hand).gesture is Gesture.MOVE


def test_fist_pauses_tracking():
    assert GestureInterpreter().interpret(pose()).gesture is Gesture.PAUSE


def test_middle_finger_pinch_with_pinky_up_drags():
    hand = pose(
        extended={Landmark.PINKY_TIP},
        touches=Landmark.MIDDLE_TIP,
    )

    assert GestureInterpreter().interpret(hand).gesture is Gesture.DRAG
