import json
import os
import sys
import tempfile

try:
    import httpx
except ImportError:         # the most common first problem: the script runs with a Python without the packages
    raise ImportError(
        f"The package 'httpx' is missing in the Python that runs this program ({sys.executable}). "
        "Usually VS Code uses another Python than your environment: choose it with "
        "'Python: Select Interpreter' (the entry with .venv), or run in the terminal: "
        "pip install -r requirements.txt (or: pip install -r dungeoncoder/requirements.txt), "
        "then check the setup with: python -m dungeoncoder") from None

from . import asciimap, generator, trace, variants
from ._api_config import BASE_URL as _CONFIGURED_BASE_URL, HOST
from ._generated import Client
from ._generated.errors import UnexpectedStatus
from ._generated.models.api_error_response import ApiErrorResponse
from ._generated.models.configure_params import ConfigureParams
from ._generated.models.distance_param import DistanceParam
from ._generated.models.name_param import NameParam
from ._generated.models.pace_params import PaceParams
from ._generated.models.tiled_level import TiledLevel
from ._generated.api.hero import (
    configure as _configure_api,
    drop as _drop_api,
    get_inventory as _get_inventory_api,
    get_items_at_position as _get_items_at_position_api,
    interact as _interact_api,
    is_abyss_in_front as _is_abyss_in_front_api,
    ask_oracle as _ask_oracle_api,
    is_at_goal as _is_at_goal_api,
    is_enemy_in_front as _is_enemy_in_front_api,
    is_collision_in_front as _is_collision_in_front_api,
    is_facing_north as _is_facing_north_api,
    sense_goal as _sense_goal_api,
    is_switch_in_front as _is_switch_in_front_api,
    is_torch_in_front as _is_torch_in_front_api,
    move as _move_api,
    peek_item_value as _peek_item_value_api,
    pickup as _pickup_api,
    read_item_value as _read_item_value_api,
    set_pace as _set_pace_api,
    turn_left as _turn_left_api,
)
from ._generated.api.level import load_level as _load_level_api, reset_level as _reset_level_api
from ._generated.api.game import get_statistics as _get_statistics_api, get_version as _get_version_api

os.environ["NO_PROXY"] = HOST


def _discover_base_url() -> str:
    """Where the game listens: DUNGEONCODER_PORT, else the port the extension wrote to
    .dungeoncoder-port in the working folder or a folder above it (setting dungeonCoder.port),
    else the default from api/openapi.yaml."""
    port = os.environ.get("DUNGEONCODER_PORT", "").strip()
    if not port.isdigit():
        port = ""
        folder = os.getcwd()
        while True:
            candidate = os.path.join(folder, ".dungeoncoder-port")
            if os.path.isfile(candidate):
                with open(candidate, encoding="utf-8") as f:
                    port = f.read().strip()
                break
            parent = os.path.dirname(folder)
            if parent == folder:
                break
            folder = parent
    return f"http://{HOST}:{port}" if port.isdigit() else _CONFIGURED_BASE_URL


DEFAULT_BASE_URL = _discover_base_url()

# move() and turn_left() return only after the animation: a step takes
# _STEP_SECONDS / pace (game/src/character.js). The server gives up on a step
# after 5 s + step time (src/extension.ts), so the client waits a bit longer.
_STEP_SECONDS = 0.5
_ACTION_TIMEOUT_SLACK = 6.0


def _extract_message(response) -> str:
    """Best-effort extraction of the server's error message from a raw HTTP response."""
    try:
        return json.loads(response.content).get("message", "")
    except (ValueError, AttributeError):
        return ""


_simulator = None      # a sim.Simulator while scripts run without the game (use_simulator)


def use_simulator(on: bool = True) -> None:
    """Runs everything in the pure-Python simulator (dungeoncoder/sim.py) instead of the
    game in VS Code: same classes, same answers, no picture, steps take no time.
    Also switched on by the environment variable DUNGEONCODER_SIM=1."""
    global _simulator
    from .sim import Simulator
    _simulator = Simulator() if on else None


def _simulated(client, sync_detailed_fn, body=None, hero=None):
    """What the generated call would return if the extension host had answered."""
    module = sys.modules[sync_detailed_fn.__module__]
    method = sync_detailed_fn.__module__.rsplit(".", 1)[1]
    params = body.to_dict() if body is not None else {}
    if hero:
        params["hero"] = hero
    status, payload = _simulator.request(method, params)
    return module._build_response(client=client, response=httpx.Response(status, json=payload))


_version_checked = False


def _check_version(base_url):
    """Once per program: does this copy of the package fit the running extension? A copied
    `dungeoncoder` folder ages with its exercise folder, and after an update of the extension
    it fails in odd ways (a method that doesn't exist yet). Only warns, never stops."""
    global _version_checked
    if _version_checked or _simulator is not None:
        return
    _version_checked = True
    from . import __version__
    try:
        response = _get_version_api.sync_detailed(client=Client(base_url=base_url, timeout=httpx.Timeout(1)))
    except Exception:
        return                  # no game running: loading the level says so
    if response.status_code == 404:
        print(f"Warning: the Dungeon Coder extension in VS Code is older than this Python package "
              f"(dungeoncoder {__version__}): some commands may be missing. Update the extension, "
              f"or check that the right Dungeon Coder runs (Extensions view).")
        return
    extension = getattr(getattr(response.parsed, "result", None), "extension", None)
    if extension and extension.split(".")[:2] != __version__.split(".")[:2]:
        print(f"Warning: this Python package (dungeoncoder {__version__}, {os.path.dirname(os.path.abspath(__file__))}) "
              f"doesn't fit the Dungeon Coder extension ({extension}). Run \"HM Dungeon Coder: Copy Python API "
              f"to workspace\" again, or: pip install --upgrade dungeoncoder")


def _call(client: Client, sync_detailed_fn, *, default, explain_refusal=False, **kwargs):
    """
    Runs a generated API call, translating transport/validation failures and
    ordinary negative business outcomes (e.g. "move blocked by a wall") into
    `default`, the same way the hand-rolled HTTP client used to. On an
    unexpected response, the server's own error message is printed so a
    student can see *why* a call failed (e.g. a bad argument type).
    """
    result = _call_unrecorded(client, sync_detailed_fn, default=default, explain_refusal=explain_refusal, **kwargs)
    body = kwargs.get("body")
    method = sync_detailed_fn.__module__.rsplit(".", 1)[1]
    params = body.to_dict() if body is not None else None
    if kwargs.get("hero"):
        params = {**(params or {}), "hero": kwargs["hero"]}
    if method == "load_level" and _simulator is not None and _simulator.level_override:
        params = _simulator.last_level_data      # grading: the level that was really played
        trace.loading(_simulator.level_override)
    trace.record(method, params, result)
    return result


def _call_unrecorded(client: Client, sync_detailed_fn, *, default, explain_refusal=False, **kwargs):
    try:
        if _simulator is not None:
            response = _simulated(client, sync_detailed_fn, **kwargs)
        else:
            response = sync_detailed_fn(client=client, **kwargs)
    except UnexpectedStatus as err:
        print(f"API error: {_extract_message(err) or err}")
        return default
    except httpx.ConnectError:
        print("Connection error occurred. Did you start the Dungeon Coder Plugin? "
              f"(looked for the game at {getattr(client, '_base_url', DEFAULT_BASE_URL)})")
        return default
    except httpx.TimeoutException:
        print("Timeout error occurred. Server took too long to respond.")
        return default
    except Exception as err:
        print(f"An unknown error occurred: {err}")
        return default

    parsed = response.parsed
    if isinstance(parsed, ApiErrorResponse):
        # explain_refusal: True prints every refusal, a string only those starting with it
        if explain_refusal is True or (explain_refusal and str(parsed.message).startswith(explain_refusal)):
            print(parsed.message)
        return default
    if parsed is None:
        message = _extract_message(response) or f"Unexpected response (HTTP {response.status_code})."
        print(f"API error: {message}")
        return default
    return parsed.result


class Hero:
    """
    A class to control the hero's actions and get its state.
    """
    BASE_URL = DEFAULT_BASE_URL

    def __init__(self, base_url: str = BASE_URL, index: int = 0):
        self._base_url = base_url
        self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))
        self._pace = 1.0
        self._action_client = self._make_action_client()
        self._index = index                 # which hero in a co-op level (0 = MainCharacter)

    def _call(self, client, fn, **kwargs):
        """_call for this hero: heroes after the first one send their index (query parameter hero)."""
        return _call(client, fn, **kwargs, **({"hero": self._index} if self._index else {}))

    def _make_action_client(self) -> Client:
        """Client for requests that wait for an animation; its timeout follows the pace."""
        read_timeout = _ACTION_TIMEOUT_SLACK + _STEP_SECONDS / self._pace
        return Client(base_url=self._base_url, timeout=httpx.Timeout(1, read=read_timeout))

    def configure(self, name: str, typeNumber: int) -> bool:
        return self._call(self._client, _configure_api.sync_detailed, default=False,
                     body=ConfigureParams(name=name, type_number=typeNumber))

    def move(self) -> bool:
        """Moves the hero one field forward. Returns False if the way is blocked (a wall, or
           another hero), or if a level with a move budget (max_moves) has no moves left."""
        return self._call(self._action_client, _move_api.sync_detailed, default=False, explain_refusal="No moves left")

    def turn_left(self) -> bool:
        """Turns the hero 90 degrees to the left."""
        return self._call(self._action_client, _turn_left_api.sync_detailed, default=False)

    def interact(self) -> bool:
        """Interacts with the object in front of the hero (torch, switch, chest, ...).
           Returns True if something reacted, False if there is nothing to interact with."""
        return self._call(self._client, _interact_api.sync_detailed, default=False)

    def is_collision_in_front(self) -> bool:
        """Checks if there is a collision in front of the hero."""
        return self._call(self._client, _is_collision_in_front_api.sync_detailed, default=False)

    def is_switch_in_front(self) -> bool:
        """Checks if there is a switch in front of the hero."""
        return self._call(self._client, _is_switch_in_front_api.sync_detailed, default=False)

    def is_facing_north(self) -> bool:
        """Checks if the hero is facing north."""
        return self._call(self._client, _is_facing_north_api.sync_detailed, default=False)

    def is_abyss_in_front(self) -> bool:
        """Checks if there is an abyss in front of the hero."""
        return self._call(self._client, _is_abyss_in_front_api.sync_detailed, default=False)

    def is_torch_in_front(self) -> bool:
        """Checks if there is a torch in front of the hero."""
        return self._call(self._client, _is_torch_in_front_api.sync_detailed, default=False)

    def sense_goal(self) -> int | None:
        """The amulet: how many fields the exit is away as the crow flies (columns plus rows,
           walls don't count), or None. Only levels with an amulet answer."""
        return self._call(self._client, _sense_goal_api.sync_detailed, default=None, explain_refusal=True)

    def is_at_goal(self) -> bool:
        """Checks if the hero stands on the goal field. Some levels also need
           win conditions (e.g. all sweets collected): see Game.get_statistics()."""
        return self._call(self._client, _is_at_goal_api.sync_detailed, default=False)

    def get_items_at_position(self) -> list[str]:
        """Returns the items at the hero's current position."""
        return self._call(self._client, _get_items_at_position_api.sync_detailed, default=[])

    def get_inventory(self) -> list[str]:
        """Returns the list of items in the hero's inventory."""
        return self._call(self._client, _get_inventory_api.sync_detailed, default=[])

    def is_enemy_in_front(self) -> bool:
        """Checks if a guard stands on the field in front of the hero."""
        return self._call(self._client, _is_enemy_in_front_api.sync_detailed, default=False)

    def ask_oracle(self) -> str | None:
        """Asks the oracle the way to the exit: the direction of the first step of a
           shortest way ("north", "east", "south" or "west"), or None if the hero stands
           on the exit or there is no way. Only levels with an oracle answer."""
        return self._call(self._client, _ask_oracle_api.sync_detailed, default=None, explain_refusal=True)

    def read_item_value(self) -> int | None:
        """Returns the value of the item on the hero's field, e.g. a crystal's weight,
           or None if no item with a value lies there. Values are never shown on screen."""
        return self._call(self._client, _read_item_value_api.sync_detailed, default=None)

    def peek_item_value(self, distance: int) -> int | None:
        """Returns the value of the item `distance` fields ahead in the direction the
           hero faces (1 = the field in front), or None if there is none. Only works in
           levels that have a Fernrohr (telescope)."""
        if type(distance) != int or distance < 1:
            print("Error: distance must be a whole number of at least 1.")
            return None
        return self._call(self._client, _peek_item_value_api.sync_detailed, default=None,
                     explain_refusal=True, body=DistanceParam(distance=distance))

    def pickup(self, name: str) -> bool:
        """Picks up the item with provided name. Use get_items_at_position()
           to check what can be picked up at the current location."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to pickup.")
            return False
        return self._call(self._client, _pickup_api.sync_detailed, default=False, body=NameParam(name=name),
                     explain_refusal="The inventory is full")

    def drop(self, name: str) -> bool:
        """Drops the item with provided name. Use get_inventory()
           to check what can be dropped."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to drop.")
            return False
        return self._call(self._client, _drop_api.sync_detailed, default=False, body=NameParam(name=name))

    def set_pace(self, factor: float) -> bool:
        """Sets the hero's speed: 1 is normal, 2 twice as fast, 0.5 half as fast."""
        if type(factor) != float and type(factor) != int:
            print("Error: Factor has to be of type 'int' or 'float'.")
            return False
        if factor <= 0:
            print("Error: Factor has to be greater than 0.")
            return False
        ok = self._call(self._client, _set_pace_api.sync_detailed, default=False, body=PaceParams(factor=factor))
        if ok:
            self._pace = factor
            self._action_client = self._make_action_client()
        return ok


class Game:
    """
    A class to interact with the hero game API.

    Attributes:
        hero: An instance of Hero, which handles hero-related commands.
        level: An instance of Level, which handles level-related commands.
    """

    BASE_URL = DEFAULT_BASE_URL

    def __init__(self, level_file, seed: int | None = None):
        """Loads the level. `seed` picks a variant of a level that has some (objects that may
        lie anywhere in a region, see variants.py): the same seed, the same variant."""
        _check_version(self.BASE_URL)
        if seed is not None and (type(seed) != int):
            print("Error: seed must be a whole number.")
            sys.exit(1)
        self.__level = self.Level(self.BASE_URL)
        try:
            trace.loading(level_file)
            loaded = self.__level.load(level_file, seed)
        except FileNotFoundError:
            print(f"Error: Level file '{level_file}' not found. "
                  f"Please check the path and that you opened the right folder in VS Code "
                  f"(current folder: {os.getcwd()}).")
            sys.exit(1)
        except json.JSONDecodeError as err:
            print(f"Error: Level file '{level_file}' is not valid JSON: {err}")
            sys.exit(1)
        except asciimap.MapError as err:
            print(f"Error: Map file '{level_file}': {err}")
            sys.exit(1)
        except ValueError as err:           # a variant that doesn't fit its region
            print(f"Error: Level '{level_file}', seed {seed}: {err}")
            sys.exit(1)
        if not loaded:
            print(f"Error: Level '{level_file}' could not be loaded (see the message above). "
                  f"Did you start Dungeon Coder (\"HM Dungeon Coder: Enter the dungeon\")?")
            sys.exit(1)

        self.__hero = Hero(self.BASE_URL)
        self.__heroes = None
        self.seed = self.__level.seed
        """The seed of this level (a generated level or a variant), or None."""

    @classmethod
    def generate(cls, seed: int | None = None, kind: str = "maze", **options) -> "Game":
        """Loads a generated level; the same seed always gives the same level.
        Without a seed, a new level each time: its seed is printed and kept in game.seed.

        Example: Game.generate(seed=7, width=21, height=15, loops=3, fog="dark")
        kind "maze": width and height odd (default 15x11), loops = extra openings
        (cycles and free-standing walls); style = the text-map style (default "maze",
        from the course's asset pack); other keywords become map properties.
        The map text is available as generator.maze_text(seed, ...)."""
        if seed is None:
            seed, _ = variants.random_seed()
            print(f"Level {kind} no. {seed} (the same again: Game.generate(seed={seed}))")
        try:
            text = generator.generate_text(seed, kind, **options)
        except asciimap.MapError as err:
            print(f"Error: Game.generate: {err}")
            sys.exit(1)
        path = os.path.join(tempfile.mkdtemp(prefix="dungeoncoder-"), f"{kind}_{seed}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return cls(path)

    def get_hero(self):
        return self.__hero

    def get_heroes(self) -> list:
        """All heroes of the level, the first one is get_hero(). A co-op level has several;
        each moves on its own, and heroes block each other like walls."""
        if self.__heroes is None:
            count = self.get_statistics().get("heroes", 1) or 1
            self.__heroes = [self.__hero] + [Hero(self.BASE_URL, i) for i in range(1, count)]
        return self.__heroes

    def save_trace(self, path: str) -> bool:
        """Writes every call made on this level so far, with what came back, to a JSON file
        (a trace: `python -m dungeoncoder replay FILE` plays it again in the game)."""
        if not trace.runs:
            print("Error: no level loaded, nothing to save.")
            return False
        self.get_statistics()
        trace.write(path, [trace.runs[-1]])
        return True

    def get_statistics(self) -> dict:
        """Counters of the current level since it was loaded, e.g.
        {"moves": 12, "turns": 5, "bumps": 1, "keyboard_moves": 0, "interactions": 2,
         "pickups": 0, "drops": 0, "sensor_calls": 30, "at_goal": False,
         "level_complete": False, "missing": ["3 sweets"], "moves_left": None, "heroes": 1}.
        "missing" lists the level's win conditions that are not met yet; "moves_left" the
        move() calls left in a level with a budget (max_moves)."""
        result = _call(self.__level._client, _get_statistics_api.sync_detailed, default=None)
        return result.to_dict() if result is not None else {}

    class Level:
        """
        A class to manage game levels.
        """
        def __init__(self, base_url):
            self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))
            self.seed = None

        def load(self, filename, seed=None):
            """
            Loads a level from a Tiled JSON file, or builds it from an ASCII map
            (a file ending in .txt, see asciimap.py for the format).

            Args:
                filename (str): The path to the level file.
            """
            if not os.path.exists(filename):
                raise FileNotFoundError(filename)

            if filename.endswith(".txt"):
                with open(filename, encoding="utf-8") as f:
                    text = f.read()
                header, _ = asciimap.parse_text(text)
                level_data = asciimap.level_from_text(text)
                random_recipe = "generate" in header and header.get("seed", ["random"])[0].lower() == "random"
            else:
                with open(filename, 'r') as f:
                    level_data = json.load(f)
                random_recipe = False
            level_data, self.seed, chosen = variants.prepare(level_data, seed)
            if self.seed is None:               # a generated level carries its seed as a map property
                self.seed = next((p.get("value") for p in level_data.get("properties", []) or []
                                  if p.get("name") == "seed" and isinstance(p.get("value"), int)), None)
            if random_recipe:
                self.seed = next((p.get("value") for p in level_data.get("properties", []) if p.get("name") == "seed"), None)
                print(f"Level no. {self.seed} (the same again: 'seed: {self.seed}' in {os.path.basename(filename)}, "
                      f"or DUNGEONCODER_SEED={self.seed})")
            elif chosen:
                print(f"Level variant {self.seed} (the same again: Game(\"{filename}\", seed={self.seed}))")

            # a refused level (e.g. a missing asset pack) prints the game's explanation
            return _call(self._client, _load_level_api.sync_detailed, default=False,
                         explain_refusal=True, body=TiledLevel.from_dict(level_data))

        def reset(self):
            """Resets the current level."""
            return _call(self._client, _reset_level_api.sync_detailed, default=False)


if os.environ.get("DUNGEONCODER_SIM", "").strip() not in ("", "0", "false", "False"):
    use_simulator()
