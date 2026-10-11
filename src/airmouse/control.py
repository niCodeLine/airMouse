"""Convierte posiciones de cámara en movimiento y filtra gestos inestables."""

from __future__ import annotations

from dataclasses import dataclass

from .gestures import Gesture
from .hand import Point


@dataclass
class CursorMapper:
    """Transforma coordenadas normalizadas de la cámara en posiciones de pantalla."""

    width: int
    height: int

    # Recorta los bordes de la cámara para alcanzar toda la pantalla.
    margin: float = 0.14

    # Menor: movimiento más suave y lento. Mayor: respuesta más rápida.
    smoothing: float = 0.35

    _previous: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        """Rechaza dimensiones, márgenes y suavizado fuera de rango."""

        if self.width <= 0 or self.height <= 0:
            raise ValueError("screen dimensions must be positive")

        if not 0 <= self.margin < 0.5:
            raise ValueError("margin must be between 0 and 0.5")

        if not 0 < self.smoothing <= 1:
            raise ValueError("smoothing must be between 0 and 1")

    def map(self, point: Point) -> tuple[float, float]:
        """Recibe un punto de la mano y devuelve (x, y) suavizados en la pantalla."""

        span = 1 - 2 * self.margin

        normalized_x = (point.x - self.margin) / span
        normalized_y = (point.y - self.margin) / span

        normalized_x = max(0.0, min(1.0, normalized_x))
        normalized_y = max(0.0, min(1.0, normalized_y))

        target_x = normalized_x * self.width
        target_y = normalized_y * self.height
        target = (target_x, target_y)

        if self._previous is None:
            result = target

        else:
            previous_x, previous_y = self._previous

            result = (
                previous_x + (target_x - previous_x) * self.smoothing,
                previous_y + (target_y - previous_y) * self.smoothing,
            )

        self._previous = result

        return result


class GestureHold:
    """Acepta un gesto cuando aparece durante varios fotogramas consecutivos."""

    def __init__(self, frames: int = 10) -> None:
        if frames < 1:
            raise ValueError("frames must be at least one")

        self.frames = frames
        self._gesture: Gesture | None = None
        self._count = 0
        self._emitted = False

    def update(self, gesture: Gesture) -> bool:
        """Devuelve True una vez por gesto sostenido; otro gesto reinicia el conteo."""

        if gesture != self._gesture:
            self._gesture = gesture
            self._count = 1
            self._emitted = False

        else:
            self._count += 1

        if self._count >= self.frames and not self._emitted:
            self._emitted = True
            return True

        return False
