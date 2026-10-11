"""Lee las opciones de terminal y arranca airMouse."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from . import runtime

# Guía de arranque: puedes editar libremente los textos y las columnas.
STARTUP_GUIDE = """
GESTO                                 ACCIÓN
Mano abierta                          Mover cursor
Pulgar + dedo medio¹                  Clic y arrastre
Pulgar + anular¹                      Clic derecho
Pulgar + índice, otros dedos arriba   Scroll al inclinar el índice
Índice arriba, separar del pulgar     Volumen
Rock 🤘, separar índice y pulgar      Brillo
Mantener puño cerrado                 Pausar
Mantener signo de paz ✌               Reanudar
Tres dedos arriba²                    Salir
Ctrl+C                                Salir desde la terminal

¹ Con el meñique levantado.
² Índice, medio y anular; pulgar tocando el meñique.
"""


def build_parser() -> argparse.ArgumentParser:
    """Devuelve las opciones de terminal con los valores de RuntimeConfig."""
    defaults = runtime.RuntimeConfig()
    parser = argparse.ArgumentParser(
        prog="airmouse",
        description="Controla macOS con gestos de la mano frente a la cámara.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--camera", type=int, default=defaults.camera, help="índice de cámara"
    )
    parser.add_argument(
        "--preview",
        action=argparse.BooleanOptionalAction,
        default=defaults.preview,
        help="mostrar la cámara; --no-preview la oculta sin detener los gestos",
    )
    parser.add_argument(
        "--pinch-threshold",
        type=float,
        default=defaults.pinch_threshold,
        metavar="RATIO",
        help="sensibilidad del contacto entre dedos",
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=defaults.smoothing,
        metavar="FACTOR",
        help="respuesta del cursor, mayor que 0 y hasta 1",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta las opciones recibidas; devuelve 0 al terminar o un código de error."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        print(STARTUP_GUIDE, flush=True)
        return runtime.run(
            runtime.RuntimeConfig(
                camera=args.camera,
                preview=args.preview,
                pinch_threshold=args.pinch_threshold,
                smoothing=args.smoothing,
            )
        )
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, ValueError) as error:
        logging.getLogger(__name__).error("No se pudo ejecutar airMouse: %s", error)
        return 2
