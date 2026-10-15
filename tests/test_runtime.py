"""Comprueba el cierre de la cámara sin usar hardware ni controlar el escritorio."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from airmouse import Gesture, GestureResult, Landmark, Point, runtime


@pytest.fixture
def devices(monkeypatch):
    camera = Mock()
    camera.isOpened.return_value = True
    camera.read.side_effect = [(True, object()), (False, None)]
    cv2 = Mock()
    cv2.VideoCapture.return_value = camera
    cv2.waitKey.return_value = -1
    tracker = Mock()
    tracker.process.return_value = SimpleNamespace(multi_hand_landmarks=[])
    hands = Mock()
    hands.return_value.__enter__ = Mock(return_value=tracker)
    hands.return_value.__exit__ = Mock(return_value=False)
    mp = SimpleNamespace(
        solutions=SimpleNamespace(
            hands=SimpleNamespace(Hands=hands), drawing_utils=Mock()
        )
    )
    mouse = Mock()
    mouse.size.return_value = (1000, 800)
    mouse.position.return_value = (500, 400)
    mouse.FAILSAFE = True

    class FailSafeException(Exception):
        pass

    mouse.FailSafeException = FailSafeException
    monkeypatch.setattr(runtime, "_dependencies", lambda: (cv2, mp, mouse))
    return SimpleNamespace(
        camera=camera, cv2=cv2, hands=hands, mouse=mouse, tracker=tracker
    )


@pytest.mark.parametrize("preview", [False, True])
def test_preview_only_changes_display_and_camera_is_released(devices, preview):
    camera, cv2 = devices.camera, devices.cv2

    assert runtime.run(runtime.RuntimeConfig(preview=preview)) != 0
    assert camera.read.called
    assert camera.release.called
    assert cv2.imshow.called is preview
    assert cv2.destroyAllWindows.called is preview


def test_camera_is_released_when_it_cannot_open(devices):
    camera = devices.camera
    camera.isOpened.return_value = False

    assert runtime.run(runtime.RuntimeConfig()) != 0
    assert camera.release.called


def test_camera_is_released_when_tracker_cannot_start(devices):
    camera, hands = devices.camera, devices.hands
    hands.side_effect = RuntimeError("tracker unavailable")

    with pytest.raises(RuntimeError):
        runtime.run(runtime.RuntimeConfig())
    assert camera.release.called


def track_frames(devices, monkeypatch, gestures):
    """Simula gestos y deja terminar el bucle sin usar cámara ni escritorio."""
    devices.camera.isOpened.side_effect = [True] * (len(gestures) + 1) + [False]
    devices.camera.read.side_effect = [(True, object()) for _ in gestures]
    landmark = SimpleNamespace(x=0.5, y=0.5, z=0.0)
    devices.tracker.process.return_value = SimpleNamespace(
        multi_hand_landmarks=[SimpleNamespace(landmark=[landmark] * len(Landmark))]
    )
    intents = [GestureResult(gesture, Point(0.5, 0.5)) for gesture in gestures]
    monkeypatch.setattr(
        runtime.GestureInterpreter, "interpret", Mock(side_effect=intents)
    )


def test_corner_does_not_abort_mouse_control(devices, monkeypatch):
    track_frames(devices, monkeypatch, [Gesture.MOVE])
    devices.mouse.position.return_value = (0, 0)

    def move_from_corner(*args, **kwargs):
        if devices.mouse.FAILSAFE:
            raise devices.mouse.FailSafeException()

    devices.mouse.moveTo.side_effect = move_from_corner

    assert runtime.run(runtime.RuntimeConfig()) == 0
    assert devices.mouse.moveTo.called
    assert devices.camera.release.called


def test_mission_control_runs_once_per_corner_entry(devices, monkeypatch):
    track_frames(devices, monkeypatch, [Gesture.MOVE] * 5)
    width, _ = devices.mouse.size.return_value
    corner = (width - 1, 0)
    devices.mouse.position.side_effect = [corner, corner, (500, 400), corner, corner]
    launch = Mock()
    monkeypatch.setattr(runtime.subprocess, "run", launch)

    assert runtime.run(runtime.RuntimeConfig()) == 0
    assert launch.call_count == 2
    assert launch.call_args.args[0] == ["open", "-a", "Mission Control"]


def test_surf_gesture_runs_once_per_hold(devices, monkeypatch):
    # Se fija la espera del ejemplo, sin fijar el ajuste del programa.
    hold = runtime.GestureHold(frames=2)
    monkeypatch.setattr(runtime, "GestureHold", lambda frames: hold)
    track_frames(
        devices,
        monkeypatch,
        [
            Gesture.MISSION_CONTROL,
            Gesture.MISSION_CONTROL,
            Gesture.MISSION_CONTROL,
            Gesture.MOVE,
            Gesture.MISSION_CONTROL,
            Gesture.MISSION_CONTROL,
        ],
    )
    launch = Mock()
    monkeypatch.setattr(runtime.subprocess, "run", launch)

    assert runtime.run(runtime.RuntimeConfig()) == 0
    assert launch.call_count == 2


def test_mission_control_failure_is_reported_without_aborting(
    devices, monkeypatch, caplog
):
    monkeypatch.setattr(runtime.subprocess, "run", Mock(side_effect=OSError()))

    runtime.Desktop(devices.mouse).show_mission_control()

    assert any(record.levelname == "WARNING" for record in caplog.records)


def test_surf_can_be_repeated_after_removing_the_hand(devices, monkeypatch):
    hold_type = runtime.GestureHold
    monkeypatch.setattr(runtime, "GestureHold", lambda frames: hold_type(frames=2))
    track_frames(devices, monkeypatch, [Gesture.MISSION_CONTROL] * 5)
    hand = devices.tracker.process.return_value
    no_hand = SimpleNamespace(multi_hand_landmarks=[])
    devices.tracker.process.side_effect = [hand, hand, no_hand, hand, hand]
    launch = Mock()
    monkeypatch.setattr(runtime.subprocess, "run", launch)

    assert runtime.run(runtime.RuntimeConfig()) == 0
    assert launch.call_count == 2


def test_mission_control_is_inactive_while_paused(devices, monkeypatch):
    hold_type = runtime.GestureHold
    monkeypatch.setattr(runtime, "GestureHold", lambda frames: hold_type(frames=1))
    track_frames(
        devices, monkeypatch, [Gesture.PAUSE, Gesture.MISSION_CONTROL, Gesture.MOVE]
    )
    width, _ = devices.mouse.size.return_value
    devices.mouse.position.side_effect = [(500, 400), (width - 1, 0), (500, 400)]
    launch = Mock()
    monkeypatch.setattr(runtime.subprocess, "run", launch)

    assert runtime.run(runtime.RuntimeConfig()) == 0
    assert not launch.called
    assert not devices.mouse.moveTo.called
