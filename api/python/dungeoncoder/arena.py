"""The referee's side of a live game (an arena): load the level, start and end the round.

A live game is a level with the map property `arena: true` and one hero per team, with the
teams' codes in the map property `codes` ("ROT-4711 BLAU-2234 ..."). It runs in one game (the
dev server on the referee's computer, `DC_HOST=0.0.0.0 npm run dev:browser`, its page on the
beamer); the teams' scripts join from their own computers with `Game.join("ROT-4711")` and
wait until the referee starts the game.

    from dungeoncoder import arena
    arena.load("arena.txt", url="http://127.0.0.1:3000")
    arena.start(url)        # or press Space on the game's page
    arena.end(url)          # or press E
    arena.statistics(url, hero=2)
"""
import json
import os

from . import asciimap, variants
from ._generated import Client
from ._generated.api.game import end_game as _end_game_api, get_statistics as _get_statistics_api, start_game as _start_game_api
from ._generated.api.level import load_level as _load_level_api
from ._generated.models.tiled_level import TiledLevel
from .dungeoncoder import DEFAULT_BASE_URL, _ANSWER_TIMEOUT, _call


def _client(url):
    return Client(base_url=(url or DEFAULT_BASE_URL).rstrip("/"), timeout=_ANSWER_TIMEOUT)


def load(level_file, url=None, seed=None):
    """Loads a level (Tiled JSON or a text map / recipe) into the game; returns True if the game
    took it. `seed` picks a variant or the generated level (as Game(level, seed=...))."""
    if level_file.endswith(".txt"):
        with open(level_file, encoding="utf-8") as f:
            data = asciimap.level_from_text(f.read())
    else:
        with open(level_file, encoding="utf-8") as f:
            data = json.load(f)
    data, _, _ = variants.prepare(data, seed)
    return bool(_call(_client(url), _load_level_api.sync_detailed, default=False, explain_refusal=True,
                      body=TiledLevel.from_dict(data)))


def start(url=None):
    """The referee starts the game: every joined hero may act from now on."""
    return bool(_call(_client(url), _start_game_api.sync_detailed, default=False, explain_refusal=True))


def end(url=None):
    """The referee ends the round: every hero stops where it is."""
    return bool(_call(_client(url), _end_game_api.sync_detailed, default=False, explain_refusal=True))


def statistics(url=None, hero=0):
    """The counters of one hero (its own in an arena), as Game.get_statistics()."""
    result = _call(_client(url), _get_statistics_api.sync_detailed, default=None, **({"hero": hero} if hero else {}))
    return result.to_dict() if result is not None else {}


def base_url():
    """The game's address the package would use (DUNGEONCODER_URL, DUNGEONCODER_PORT, ...)."""
    return os.environ.get("DUNGEONCODER_URL", "").rstrip("/") or DEFAULT_BASE_URL
