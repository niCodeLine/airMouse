"""Comprueba opciones y errores sin abrir la cámara ni mover el ratón."""

import pytest

from airmouse import runtime
from airmouse.cli import main


@pytest.mark.parametrize(
    "arguments, preview", [(["--preview"], True), (["--no-preview"], False)]
)
def test_preview_option_reaches_runtime(monkeypatch, arguments, preview):
    received = []
    monkeypatch.setattr(runtime, "run", lambda config: received.append(config) or 0)

    assert main(arguments) == 0
    assert received[0].preview is preview


def test_cli_uses_the_configured_default(monkeypatch):
    received = []
    monkeypatch.setattr(runtime, "run", lambda config: received.append(config) or 0)

    assert main([]) == 0
    assert received[0] == runtime.RuntimeConfig()


def test_startup_failure_returns_an_error(monkeypatch):
    def unavailable_camera(config):
        raise RuntimeError("camera unavailable")

    monkeypatch.setattr(runtime, "run", unavailable_camera)
    assert main([]) != 0
