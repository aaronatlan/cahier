"""Point d'entrée de l'app : démarre le serveur local puis ouvre la fenêtre native."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import uvicorn
import webview

from .server import app

HOST = "127.0.0.1"
PORT = 8743
ICON_PATH = Path(__file__).parent / "icon.icns"
APP_NAME = "Cahier"


def _brand_dock_icon() -> None:
    """Le binaire Python.framework lancé par notre .app garde l'identité (et l'icône)
    de 'Python' aux yeux de macOS. On force le nom et l'icône du Dock/menu bar au
    démarrage pour que ça se voie et se nomme "Cahier" plutôt que "Python"."""
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSProcessInfo

        NSProcessInfo.processInfo().setProcessName_(APP_NAME)
        if ICON_PATH.exists():
            icon = NSImage.alloc().initByReferencingFile_(str(ICON_PATH))
            if icon is not None:
                NSApplication.sharedApplication().setApplicationIconImage_(icon)
    except Exception:
        pass  # pas macOS, ou PyObjC indisponible : pas bloquant


def _run_server() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_until_ready(timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.3):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Le serveur local n'a pas démarré à temps.")


def _on_main_thread(func) -> None:
    """Les méthodes exposées à pywebview.api sont invoquées depuis le thread du pont
    JS, pas le thread principal — appeler des méthodes AppKit (destroy/minimize/...)
    depuis là est silencieusement ignoré par Cocoa. On repasse par le run loop
    principal via PyObjCTools.AppHelper avant d'agir sur la fenêtre."""
    try:
        from PyObjCTools import AppHelper

        AppHelper.callAfter(func)
    except Exception:
        func()  # pas macOS / PyObjC indisponible : on tente en direct


class WindowAPI:
    """Exposée en JS via `pywebview.api.*` pour piloter la fenêtre depuis la fausse
    barre de titre dessinée dans l'UI (fenêtre frameless, donc pas de contrôles natifs)."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None

    def bind(self, window: webview.Window) -> None:
        self._window = window

    def close(self) -> None:
        # window.destroy() de pywebview est un no-op silencieux en mode frameless sur
        # cette configuration (bug/incompatibilité constaté en debug). Cahier est une
        # app mono-fenêtre : fermer la fenêtre = quitter l'app, donc on appelle
        # directement NSApplication.terminate_, qui fonctionne de manière fiable.
        def _terminate():
            from AppKit import NSApplication

            NSApplication.sharedApplication().terminate_(None)

        _on_main_thread(_terminate)

    def minimize(self) -> None:
        if self._window:
            _on_main_thread(self._window.minimize)

    def toggle_fullscreen(self) -> None:
        if self._window:
            _on_main_thread(self._window.toggle_fullscreen)


def _disable_window_restoration() -> None:
    """macOS partage l'identité de bundle 'org.python.python' entre tous les lancements
    (voir _brand_dock_icon), ce qui pousse parfois AppKit à restaurer l'état de fenêtre
    d'un lancement précédent (dernier onglet ouvert) au lieu de démarrer sur la
    bibliothèque. On marque la fenêtre comme non-restaurable côté AppKit — plus propre
    qu'un rechargement JS forcé, qui cassait le pont pywebview.api (boutons de la barre
    de titre custom inertes)."""
    try:
        from AppKit import NSApplication

        for win in NSApplication.sharedApplication().windows():
            win.setRestorable_(False)
    except Exception:
        pass


def main() -> None:
    _brand_dock_icon()
    threading.Thread(target=_run_server, daemon=True).start()
    _wait_until_ready()

    api = WindowAPI()
    window = webview.create_window(
        APP_NAME,
        f"http://{HOST}:{PORT}",
        width=1200,
        height=800,
        min_size=(960, 640),
        frameless=True,
        easy_drag=False,
        js_api=api,
    )
    api.bind(window)
    # `webview.start(func)` exécute `func` sur un thread à part : des appels AppKit
    # (non thread-safe) depuis ce thread ont rendu la fenêtre totalement inerte aux
    # clics/frappes lors d'un précédent essai. `window.events.shown` s'exécute lui dans
    # le contexte normal des événements pywebview, comme `loaded` — donc sûr ici.
    window.events.shown += _disable_window_restoration
    webview.start()


if __name__ == "__main__":
    main()
