"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airmouse",
        description="Control macOS with camera-tracked hand gestures.",
    )
    parser.add_argument(
        "--camera", type=int, default=0, help="camera index (default: 0)"
    )
    parser.add_argument(
        "--no-preview", action="store_true", help="hide the camera preview"
    )
    parser.add_argument(
        "--pinch-threshold",
        type=float,
        default=0.32,
        metavar="RATIO",
        help="finger-touch sensitivity (default: 0.32)",
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=0.35,
        metavar="FACTOR",
        help="cursor response from 0 to 1 (default: 0.35)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .runtime import RuntimeConfig, run

    try:
        return run(
            RuntimeConfig(
                camera=args.camera,
                preview=not args.no_preview,
                pinch_threshold=args.pinch_threshold,
                smoothing=args.smoothing,
            )
        )
    except (RuntimeError, ValueError) as error:
        print(f"airMouse could not start: {error}")
        return 2
