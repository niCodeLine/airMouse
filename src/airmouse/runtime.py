"""Camera loop and macOS side effects, imported only when the app runs.

This module connects all the pieces of airMouse:

- reads frames from the webcam
- asks MediaPipe for hand landmarks
- interprets those landmarks as gestures
- controls the macOS desktop
- draws the optional camera preview

The actual hand geometry and gesture rules live elsewhere so this file can
focus on the messy real-world part: camera input, desktop actions, and visuals.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass

from .control import CursorMapper, GestureHold
from .gestures import Gesture, GestureInterpreter
from .hand import HandLandmarks, Landmark, Point


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime options used when starting airMouse."""

    camera: int = 0
    preview: bool = True
    pinch_threshold: float = 0.32
    smoothing: float = 0.35


class Desktop:
    """Small adapter around the macOS desktop automation APIs."""

    def __init__(self, pyautogui) -> None:
        self.gui = pyautogui

        # Keep PyAutoGUI's emergency corner failsafe enabled.
        self.gui.FAILSAFE = True

    def set_volume(self, value: float) -> None:
        """Set macOS output volume from 0 to 100."""

        subprocess.run(
            [
                "osascript",
                "-e",
                f"set volume output volume {round(value)}",
            ],
            check=False,
            capture_output=True,
        )

    def set_brightness(self, value: float) -> None:
        """Set display brightness if the optional `brightness` tool exists."""

        executable = shutil.which("brightness")

        if executable:
            subprocess.run(
                [executable, str(value / 100)],
                check=False,
                capture_output=True,
            )


def bubblegum(value: float, max_thickness: int = 15, min_thickness: int = 2,) -> int:
    """Return the thickness of the volume/brightness elastic line.

    This is mostly a visual toy from the original airMouse.

    When thumb and index are close together the line becomes thick, and as
    they move apart it becomes thinner, making it look a little like a piece
    of bubblegum being stretched between the fingers.

    `value` is the same 0-100 value used for volume and brightness.
    """

    if value < 20:
        return max_thickness

    if value > 90:
        return min_thickness

    # Linear interpolation between:
    #
    # value = 20  -> max_thickness
    # value = 90-100 -> min_thickness
    slope = (min_thickness - max_thickness) / (100 - 20)
    intercept = max_thickness - slope * 20

    return int(slope * value + intercept)


def _dependencies():
    """Import heavyweight runtime dependencies only when the app actually runs."""

    try:
        import cv2
        import mediapipe as mp
        import pyautogui

    except ImportError as error:
        raise RuntimeError(
            'runtime dependencies are missing; '
            'install with "pip install -e .[runtime]"'
        ) from error

    return cv2, mp, pyautogui


def _landmark_pixel(
    hand: HandLandmarks,
    landmark: Landmark,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int]:
    """Convert one normalized hand landmark into OpenCV pixel coordinates."""

    point = hand[landmark]

    return (
        int(point.x * frame_width),
        int(point.y * frame_height),
    )


def _draw_bubblegum(
    cv2,
    frame,
    hand: HandLandmarks,
    gesture: Gesture,
    value: float,
) -> None:
    """Draw the elastic thumb-to-index control for volume or brightness.

    The line follows the actual thumb and index fingertips. Its length therefore
    changes naturally with the hand, while `bubblegum()` changes its thickness.

    This has no effect on gesture recognition or desktop control; it is purely
    part of the camera preview.
    """

    frame_height, frame_width = frame.shape[:2]

    thumb = _landmark_pixel(
        hand,
        Landmark.THUMB_TIP,
        frame_width,
        frame_height,
    )

    index = _landmark_pixel(
        hand,
        Landmark.INDEX_TIP,
        frame_width,
        frame_height,
    )

    thickness = bubblegum(value)

    # The bubblegum line.
    cv2.line(
        frame,
        thumb,
        index,
        color=(255, 0, 255),
        thickness=thickness,
    )

    if gesture is Gesture.VOLUME:
        label = f"Volume: {round(value)}"
        text_color = (255, 0, 0)

    else:
        label = f"Brightness: {round(value)}"
        text_color = (0, 255, 255)

    # Place the value near the index fingertip.
    text_x = index[0] + 15
    text_y = index[1] - 15

    cv2.putText(
        frame,
        label,
        (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        text_color,
        2,
    )


def run(config: RuntimeConfig) -> int:
    """Start camera tracking and return a process exit code."""

    cv2, mp, pyautogui = _dependencies()

    desktop = Desktop(pyautogui)

    width, height = pyautogui.size()

    mapper = CursorMapper(
        width,
        height,
        smoothing=config.smoothing,
    )

    interpreter = GestureInterpreter(
        config.pinch_threshold,
    )

    # Commands such as PAUSE and QUIT should remain visible for several
    # consecutive frames before they are accepted.
    command_hold = GestureHold(12)

    camera = cv2.VideoCapture(config.camera)

    hands_api = mp.solutions.hands
    drawing = mp.solutions.drawing_utils

    paused = False
    dragging = False

    # Prevent a held right-click gesture from clicking continuously every frame.
    last_right_click = 0.0

    if not camera.isOpened():
        print(f"Could not open camera {config.camera}.")
        return 1

    try:
        with hands_api.Hands(
            max_num_hands=1,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.65,
        ) as tracker:

            while camera.isOpened():
                ok, frame = camera.read()

                if not ok:
                    print("The camera stopped returning frames.")
                    return 1

                # Mirror the image so hand movement feels natural.
                frame = cv2.flip(frame, 1)

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                result = tracker.process(rgb_frame)

                if result.multi_hand_landmarks:
                    tracked = result.multi_hand_landmarks[0]

                    # Convert MediaPipe's landmarks into our dependency-free
                    # hand representation.
                    hand = HandLandmarks(
                        Point(item.x, item.y, item.z)
                        for item in tracked.landmark
                    )

                    intent = interpreter.interpret(hand)

                    # Only command-like gestures really care about stability,
                    # but passing every gesture through GestureHold also resets
                    # the counter whenever the hand pose changes.
                    stable = command_hold.update(intent.gesture)

                    # ------------------------------------------------------
                    # Commands
                    # ------------------------------------------------------

                    if stable and intent.gesture is Gesture.QUIT:
                        break

                    if stable and intent.gesture is Gesture.PAUSE:
                        paused = True

                    if stable and intent.gesture is Gesture.RESUME:
                        paused = False

                    # ------------------------------------------------------
                    # Desktop control
                    # ------------------------------------------------------

                    if not paused:
                        x, y = mapper.map(intent.cursor)

                        # MOVE and DRAG both follow the hand.
                        if intent.gesture in {
                            Gesture.MOVE,
                            Gesture.DRAG,
                        }:
                            pyautogui.moveTo(
                                x,
                                y,
                                _pause=False,
                            )

                        # Start dragging once.
                        if (
                            intent.gesture is Gesture.DRAG
                            and not dragging
                        ):
                            pyautogui.mouseDown(
                                button="left",
                                _pause=False,
                            )
                            dragging = True

                        # Release as soon as the drag gesture disappears.
                        elif (
                            intent.gesture is not Gesture.DRAG
                            and dragging
                        ):
                            pyautogui.mouseUp(
                                button="left",
                                _pause=False,
                            )
                            dragging = False

                        # Right-click with a small cooldown so one held gesture
                        # does not produce dozens of clicks.
                        if (
                            intent.gesture is Gesture.RIGHT_CLICK
                            and time.monotonic() - last_right_click > 0.5
                        ):
                            pyautogui.rightClick(_pause=False)
                            last_right_click = time.monotonic()

                        if (
                            intent.gesture is Gesture.SCROLL
                            and intent.value
                        ):
                            pyautogui.scroll(
                                round(intent.value * 2),
                                _pause=False,
                            )

                        if (
                            intent.gesture is Gesture.VOLUME
                            and intent.value is not None
                        ):
                            desktop.set_volume(intent.value)

                        if (
                            intent.gesture is Gesture.BRIGHTNESS
                            and intent.value is not None
                        ):
                            desktop.set_brightness(intent.value)

                    # ------------------------------------------------------
                    # Preview
                    # ------------------------------------------------------

                    if config.preview:
                        drawing.draw_landmarks(
                            frame,
                            tracked,
                            hands_api.HAND_CONNECTIONS,
                        )

                        # Bring back the original bubblegum visual when using
                        # the thumb/index continuous controls.
                        if (
                            intent.gesture
                            in {
                                Gesture.VOLUME,
                                Gesture.BRIGHTNESS,
                            }
                            and intent.value is not None
                        ):
                            _draw_bubblegum(
                                cv2,
                                frame,
                                hand,
                                intent.gesture,
                                intent.value,
                            )

                        state = "(-_-)~ paused" if paused else "(*_*)' active "
                        status = intent.gesture.value

                        # intention
                        cv2.putText(
                            frame,                      # image
                            status.upper(),             # text
                            (20, 40),                   # position
                            cv2.FONT_HERSHEY_SIMPLEX,   # font
                            0.8,                        # scale
                            (0, 255, 255),              # color
                            2,                          # thickness
                        )

                        # status
                        cv2.putText(
                            frame,                      # image
                            state,                      # text
                            (20, 70),                   # position
                            cv2.FONT_HERSHEY_SIMPLEX,   # font
                            0.8,                        # scale
                            (0, 255, 255),              # color
                            2,                          # thickness
                        )

                if config.preview:
                    cv2.imshow(
                        "airMouse · press Q to quit",
                        frame,
                    )

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

    finally:
        # Never leave the mouse button held if the program closes halfway
        # through a drag.
        if dragging:
            pyautogui.mouseUp(
                button="left",
                _pause=False,
            )

        camera.release()
        cv2.destroyAllWindows()

    return 0