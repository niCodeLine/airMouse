"""Comprueba el cierre de la cámara sin usar hardware ni controlar el escritorio."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from airmouse import runtime


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
    monkeypatch.setattr(runtime, "_dependencies", lambda: (cv2, mp, mouse))
    return camera, cv2, hands


@pytest.mark.parametrize("preview", [False, True])
def test_preview_only_changes_display_and_camera_is_released(devices, preview):
    camera, cv2, _ = devices

    assert runtime.run(runtime.RuntimeConfig(preview=preview)) != 0
    assert camera.read.called
    assert camera.release.called
    assert cv2.imshow.called is preview
    assert cv2.destroyAllWindows.called is preview


def test_camera_is_released_when_it_cannot_open(devices):
    camera, _, _ = devices
    camera.isOpened.return_value = False

    assert runtime.run(runtime.RuntimeConfig()) != 0
    assert camera.release.called


def test_camera_is_released_when_tracker_cannot_start(devices):
    camera, _, hands = devices
    hands.side_effect = RuntimeError("tracker unavailable")

    with pytest.raises(RuntimeError):
        runtime.run(runtime.RuntimeConfig())
    assert camera.release.called
