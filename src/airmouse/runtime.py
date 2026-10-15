"""Conecta cámara, reconocimiento, acciones de macOS y vista opcional."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass

from .control import CursorMapper, GestureHold
from .gestures import Gesture, GestureInterpreter, GestureResult
from .hand import HandLandmarks, Landmark, Point

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    """Valores de arranque, compartidos por Python y la línea de comandos."""

    camera: int = 0
    # VISTA DE CÁMARA: False la oculta; True la muestra. La cámara sigue trabajando.
    # En terminal, --preview y --no-preview sustituyen este valor para esa ejecución.
    preview: bool = False
    pinch_threshold: float = 0.32
    smoothing: float = 0.35


class Desktop:
    """Acceso a los controles de macOS."""

    def __init__(self, pyautogui) -> None:
        self.gui = pyautogui
        # Las esquinas no detienen airMouse; se sale con Ctrl+C o el gesto de salida.
        self.gui.FAILSAFE = False

    def show_mission_control(self) -> None:
        """Abre Mission Control con la aplicación de macOS; avisa si falla."""
        try:
            subprocess.run(
                ["open", "-a", "Mission Control"], check=True, capture_output=True
            )
        except (OSError, subprocess.CalledProcessError) as error:
            logger.warning("No se pudo abrir Mission Control: %s", error)

    def set_volume(self, value: float) -> None:
        """Establece el volumen de macOS con un porcentaje de 0 a 100."""
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {round(value)}"],
            check=False,
            capture_output=True,
        )

    def set_brightness(self, value: float) -> None:
        """Ajusta el brillo de 0 a 100 si está instalada la utilidad brightness."""
        executable = shutil.which("brightness")
        if executable:
            subprocess.run(
                [executable, str(value / 100)], check=False, capture_output=True
            )


def bubblegum(value: float, max_thickness: int = 15, min_thickness: int = 2) -> int:
    """Devuelve el grosor de la línea entre dedos para un valor de 0 a 100."""
    if value < 20:
        return max_thickness
    if value > 90:
        return min_thickness

    slope = (min_thickness - max_thickness) / (100 - 20)
    intercept = max_thickness - slope * 20
    return int(slope * value + intercept)


def _dependencies():
    """Carga las bibliotecas de cámara y escritorio sólo cuando se inicia el control."""
    try:
        import cv2
        import mediapipe as mp
        import pyautogui
    except ImportError as error:
        raise RuntimeError(
            'Desde el repositorio, instala con pipx install ".[runtime]".'
        ) from error
    return cv2, mp, pyautogui


def _landmark_pixel(
    hand: HandLandmarks,
    landmark: Landmark,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int]:
    """Convierte un punto normalizado de la mano en coordenadas de imagen."""
    point = hand[landmark]
    return int(point.x * frame_width), int(point.y * frame_height)


def _draw_bubblegum(
    cv2, frame, hand: HandLandmarks, gesture: Gesture, value: float
) -> None:
    """Dibuja la separación de los dedos y el valor de volumen o brillo."""
    frame_height, frame_width = frame.shape[:2]
    thumb = _landmark_pixel(hand, Landmark.THUMB_TIP, frame_width, frame_height)
    index = _landmark_pixel(hand, Landmark.INDEX_TIP, frame_width, frame_height)
    cv2.line(frame, thumb, index, color=(255, 0, 255), thickness=bubblegum(value))

    if gesture is Gesture.VOLUME:
        label, text_color = f"Volume: {round(value)}", (255, 0, 0)
    else:
        label, text_color = f"Brightness: {round(value)}", (0, 255, 255)

    cv2.putText(
        frame,
        label,
        (index[0] + 15, index[1] - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        text_color,
        2,
    )


def _draw_preview(
    cv2, mp, frame, tracked, hand: HandLandmarks, intent: GestureResult, paused: bool
) -> None:
    """Añade a la imagen los puntos de la mano, el gesto y el estado del control."""
    mp.solutions.drawing_utils.draw_landmarks(
        frame, tracked, mp.solutions.hands.HAND_CONNECTIONS
    )
    if (
        intent.gesture in {Gesture.VOLUME, Gesture.BRIGHTNESS}
        and intent.value is not None
    ):
        _draw_bubblegum(cv2, frame, hand, intent.gesture, intent.value)

    state = "(-_-)~ paused" if paused else "(*_*)' active "
    cv2.putText(
        frame,
        intent.gesture.value.upper(),
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
    )
    cv2.putText(frame, state, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)


def run(config: RuntimeConfig) -> int:
    """Procesa la cámara hasta salir; devuelve 0 al terminar y 1 si falla la captura."""
    cv2, mp, pyautogui = _dependencies()
    desktop = Desktop(pyautogui)
    screen_width, screen_height = pyautogui.size()
    mapper = CursorMapper(screen_width, screen_height, smoothing=config.smoothing)
    interpreter = GestureInterpreter(config.pinch_threshold)
    command_hold = GestureHold(12)

    paused = False
    dragging = False
    last_right_click = 0.0
    # Zona de activación en píxeles, en la esquina superior derecha.
    corner_size = 10
    was_in_corner = False
    camera = cv2.VideoCapture(config.camera)

    try:
        if not camera.isOpened():
            logger.error("No se pudo abrir la cámara %s.", config.camera)
            return 1

        logger.info(
            "Cámara %s · vista %s · Ctrl+C para salir.",
            config.camera,
            "visible" if config.preview else "oculta",
        )
        with mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.65,
        ) as tracker:
            while camera.isOpened():
                frame_received, frame = camera.read()
                if not frame_received:
                    logger.error("La cámara dejó de enviar imágenes.")
                    return 1

                # El espejo hace que el cursor acompañe el movimiento de la mano.
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = tracker.process(rgb_frame)

                mission_control_requested = False
                if result.multi_hand_landmarks:
                    tracked = result.multi_hand_landmarks[0]
                    hand = HandLandmarks(
                        Point(item.x, item.y, item.z) for item in tracked.landmark
                    )
                    intent = interpreter.interpret(hand)
                    gesture = intent.gesture
                    stable = command_hold.update(gesture)

                    # Pausa, reanudación y salida requieren varios fotogramas estables.
                    if stable and gesture is Gesture.QUIT:
                        break
                    if stable and gesture is Gesture.PAUSE:
                        paused = True
                    if stable and gesture is Gesture.RESUME:
                        paused = False

                    if not paused:
                        mission_control_requested = (
                            stable and gesture is Gesture.MISSION_CONTROL
                        )
                        x, y = mapper.map(intent.cursor)
                        if gesture in {Gesture.MOVE, Gesture.DRAG}:
                            pyautogui.moveTo(x, y, _pause=False)

                        # El botón se mantiene pulsado mientras dura el arrastre.
                        if gesture is Gesture.DRAG and not dragging:
                            pyautogui.mouseDown(button="left", _pause=False)
                            dragging = True
                        elif gesture is not Gesture.DRAG and dragging:
                            pyautogui.mouseUp(button="left", _pause=False)
                            dragging = False

                        # Evita repetir el clic en cada fotograma de un gesto sostenido.
                        if (
                            gesture is Gesture.RIGHT_CLICK
                            and time.monotonic() - last_right_click > 0.5
                        ):
                            pyautogui.rightClick(_pause=False)
                            last_right_click = time.monotonic()
                        if gesture is Gesture.SCROLL and intent.value:
                            pyautogui.scroll(round(intent.value * 2), _pause=False)
                        if gesture is Gesture.VOLUME and intent.value is not None:
                            desktop.set_volume(intent.value)
                        if gesture is Gesture.BRIGHTNESS and intent.value is not None:
                            desktop.set_brightness(intent.value)

                    if config.preview:
                        _draw_preview(cv2, mp, frame, tracked, hand, intent, paused)

                else:
                    # Retirar la mano permite volver a activar un gesto sostenido.
                    command_hold = GestureHold(command_hold.frames)

                cursor_x, cursor_y = pyautogui.position()
                in_corner = (
                    screen_width - corner_size <= cursor_x < screen_width
                    and 0 <= cursor_y < corner_size
                )
                if (
                    not paused
                    and not dragging
                    and (mission_control_requested or (in_corner and not was_in_corner))
                ):
                    desktop.show_mission_control()
                was_in_corner = in_corner

                # Ocultar la ventana no detiene la captura ni el reconocimiento.
                if config.preview:
                    cv2.imshow("airMouse · press Q to quit", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    finally:
        try:
            if dragging:
                pyautogui.mouseUp(button="left", _pause=False)
        finally:
            camera.release()
            if config.preview:
                cv2.destroyAllWindows()

    return 0
