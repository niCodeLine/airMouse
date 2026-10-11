"""Decide el gesto a partir de la geometría de la mano, sin controlar dispositivos."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .hand import HandLandmarks, Landmark, Point


class Gesture(str, Enum):
    """Gestos disponibles. Su orden de detección se establece en interpret()."""

    MOVE = "move"
    DRAG = "drag"
    RIGHT_CLICK = "right_click"
    SCROLL = "scroll"
    VOLUME = "volume"
    BRIGHTNESS = "brightness"

    PAUSE = "pause"
    RESUME = "resume"
    QUIT = "quit"


@dataclass(frozen=True)
class GestureResult:
    """Gesto, punto del cursor y valor: porcentaje o intensidad de desplazamiento."""

    gesture: Gesture
    cursor: Point
    value: float | None = None


class GestureInterpreter:
    """Interpreta la mano con un umbral ajustable de contacto entre dedos."""

    def __init__(self, pinch_threshold: float = 0.32) -> None:
        if pinch_threshold <= 0:
            raise ValueError("pinch_threshold must be positive")

        self.pinch_threshold = pinch_threshold

    def _touches(self, hand: HandLandmarks, finger: Landmark) -> bool:
        """Detecta contacto con el pulgar, ajustado al tamaño de la mano."""

        distance = hand.normalized_distance(Landmark.THUMB_TIP, finger)

        return distance <= self.pinch_threshold

    @staticmethod
    def _range_value(distance: float) -> float:
        """Convierte la separación de los dedos en un porcentaje limitado a 0–100."""

        minimum = 0.35
        maximum = 1.75

        value = (distance - minimum) * 100 / (maximum - minimum)

        return max(0.0, min(100.0, value))

    @staticmethod
    def _scroll_value(hand: HandLandmarks) -> float:
        """Devuelve la dirección e intensidad de desplazamiento, entre -1 y 1."""

        mcp = hand[Landmark.INDEX_MCP]
        pip = hand[Landmark.INDEX_PIP]

        dx = pip.x - mcp.x
        dy = pip.y - mcp.y

        angle = math.atan2(dy, dx)

        value = -math.sin(angle)

        return max(-1.0, min(1.0, value))

    def interpret(self, hand: HandLandmarks) -> GestureResult:
        """Devuelve el primer gesto que coincide; movimiento es la última opción."""

        index_extended = hand.finger_extended(Landmark.INDEX_TIP, Landmark.INDEX_PIP)
        middle_extended = hand.finger_extended(Landmark.MIDDLE_TIP, Landmark.MIDDLE_PIP)
        ring_extended = hand.finger_extended(Landmark.RING_TIP, Landmark.RING_PIP)
        pinky_extended = hand.finger_extended(Landmark.PINKY_TIP, Landmark.PINKY_PIP)
        thumb_extended = hand.thumb_extended()

        # La palma tiembla menos que las puntas de los dedos.
        cursor = hand[Landmark.MIDDLE_MCP]

        thumb_index_distance = hand.normalized_distance(
            Landmark.THUMB_TIP,
            Landmark.INDEX_TIP,
        )

        thumb_touching_pinky = self._touches(hand, Landmark.PINKY_TIP)

        # Salir: índice, corazón y anular arriba; pulgar tocando el meñique.
        if (
            index_extended
            and middle_extended
            and ring_extended
            and thumb_touching_pinky
        ):
            return GestureResult(gesture=Gesture.QUIT, cursor=cursor)

        # Pausa: puño cerrado. Reanudar: índice y corazón levantados.
        if not any(
            (
                thumb_extended,
                index_extended,
                middle_extended,
                ring_extended,
                pinky_extended,
            )
        ):
            return GestureResult(gesture=Gesture.PAUSE, cursor=cursor)

        if (
            index_extended
            and middle_extended
            and not ring_extended
            and not pinky_extended
        ):
            return GestureResult(gesture=Gesture.RESUME, cursor=cursor)

        # Brillo: índice y meñique arriba. Volumen: sólo el índice.
        if (
            thumb_extended
            and index_extended
            and pinky_extended
            and not middle_extended
            and not ring_extended
        ):
            brightness = self._range_value(thumb_index_distance)

            return GestureResult(
                gesture=Gesture.BRIGHTNESS,
                cursor=cursor,
                value=brightness,
            )

        if (
            index_extended
            and not middle_extended
            and not ring_extended
            and not pinky_extended
        ):
            volume = self._range_value(thumb_index_distance)

            return GestureResult(gesture=Gesture.VOLUME, cursor=cursor, value=volume)

        # Con el meñique arriba: anular para clic derecho, corazón para arrastrar.
        if self._touches(hand, Landmark.RING_TIP) and pinky_extended:
            return GestureResult(gesture=Gesture.RIGHT_CLICK, cursor=cursor)

        if self._touches(hand, Landmark.MIDDLE_TIP) and pinky_extended:
            return GestureResult(gesture=Gesture.DRAG, cursor=cursor)

        # Desplazar: pulgar e índice juntos y los otros tres dedos arriba.
        if (
            self._touches(hand, Landmark.INDEX_TIP)
            and middle_extended
            and ring_extended
            and pinky_extended
        ):
            scroll = self._scroll_value(hand)

            return GestureResult(gesture=Gesture.SCROLL, cursor=cursor, value=scroll)

        return GestureResult(gesture=Gesture.MOVE, cursor=cursor)
