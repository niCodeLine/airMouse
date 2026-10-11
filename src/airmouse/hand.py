"""Geometría de la mano, independiente de la cámara y del escritorio."""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import IntEnum


class Landmark(IntEnum):
    """Los 21 puntos: MCP es nudillo, PIP/IP articulación y TIP punta del dedo."""

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
    """Punto de la mano: x e y normalizados; z indica profundidad relativa."""

    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: Point) -> float:
        """Devuelve la distancia 3D desde este punto hasta otro."""

        return math.dist((self.x, self.y, self.z), (other.x, other.y, other.z))


class HandLandmarks(Sequence[Point]):
    """Guarda los 21 puntos; se consultan por nombre, como hand[Landmark.INDEX_TIP]."""

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
        """Devuelve el tamaño de la palma, usado para normalizar distancias."""

        wrist = self[Landmark.WRIST]
        middle_mcp = self[Landmark.MIDDLE_MCP]

        size = wrist.distance_to(middle_mcp)

        # Evita dividir por cero cuando el detector devuelve puntos coincidentes.
        return max(size, 1e-6)

    def normalized_distance(
        self,
        first: Landmark,
        second: Landmark,
    ) -> float:
        """Devuelve la distancia entre dos puntos dividida por el tamaño de la palma."""

        distance = self[first].distance_to(self[second])

        return distance / self.palm_size

    def finger_extended(
        self,
        tip: Landmark,
        pip: Landmark,
        *,
        threshold: float = 1.15,
    ) -> bool:
        """Indica si la punta supera a la articulación en distancia a la muñeca."""

        wrist = self[Landmark.WRIST]

        tip_distance = wrist.distance_to(self[tip])
        pip_distance = wrist.distance_to(self[pip])

        return tip_distance > pip_distance * threshold

    def thumb_extended(self, *, threshold: float = 1.15) -> bool:
        """Detecta el pulgar extendido respecto al nudillo del meñique."""

        anchor = self[Landmark.PINKY_MCP]

        thumb_tip_distance = anchor.distance_to(self[Landmark.THUMB_TIP])
        thumb_ip_distance = anchor.distance_to(self[Landmark.THUMB_IP])

        return thumb_tip_distance > thumb_ip_distance * threshold
