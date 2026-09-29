import json
import os
import sys
import tempfile

import httpx

from . import asciimap, generator
from ._api_config import BASE_URL as DEFAULT_BASE_URL, HOST
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
    is_at_goal as _is_at_goal_api,
    is_collision_in_front as _is_collision_in_front_api,
    is_facing_north as _is_facing_north_api,
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
from ._generated.api.game import get_statistics as _get_statistics_api

os.environ["NO_PROXY"] = HOST

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


def _call(client: Client, sync_detailed_fn, *, default, explain_refusal=False, **kwargs):
    """
    Runs a generated API call, translating transport/validation failures and
    ordinary negative business outcomes (e.g. "move blocked by a wall") into
    `default`, the same way the hand-rolled HTTP client used to. On an
    unexpected response, the server's own error message is printed so a
    student can see *why* a call failed (e.g. a bad argument type).
    """
    try:
        response = sync_detailed_fn(client=client, **kwargs)
    except UnexpectedStatus as err:
        print(f"API error: {_extract_message(err) or err}")
        return default
    except httpx.ConnectError:
        print("Connection error occurred. Did you start the Dungeon Coder Plugin?")
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

    def __init__(self, base_url: str = BASE_URL):
        self._base_url = base_url
        self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))
        self._pace = 1.0
        self._action_client = self._make_action_client()

    def _make_action_client(self) -> Client:
        """Client for requests that wait for an animation; its timeout follows the pace."""
        read_timeout = _ACTION_TIMEOUT_SLACK + _STEP_SECONDS / self._pace
        return Client(base_url=self._base_url, timeout=httpx.Timeout(1, read=read_timeout))

    def configure(self, name: str, typeNumber: int) -> bool:
        return _call(self._client, _configure_api.sync_detailed, default=False,
                     body=ConfigureParams(name=name, type_number=typeNumber))

    def move(self) -> bool:
        """Moves the hero one field forward. Returns False if the way is blocked."""
        return _call(self._action_client, _move_api.sync_detailed, default=False)

    def turn_left(self) -> bool:
        """Turns the hero 90 degrees to the left."""
        return _call(self._action_client, _turn_left_api.sync_detailed, default=False)

    def interact(self) -> bool:
        """Interacts with the object in front of the hero (torch, switch, chest, ...).
           Returns True if something reacted, False if there is nothing to interact with."""
        return _call(self._client, _interact_api.sync_detailed, default=False)

    def is_collision_in_front(self) -> bool:
        """Checks if there is a collision in front of the hero."""
        return _call(self._client, _is_collision_in_front_api.sync_detailed, default=False)

    def is_switch_in_front(self) -> bool:
        """Checks if there is a switch in front of the hero."""
        return _call(self._client, _is_switch_in_front_api.sync_detailed, default=False)

    def is_facing_north(self) -> bool:
        """Checks if the hero is facing north."""
        return _call(self._client, _is_facing_north_api.sync_detailed, default=False)

    def is_abyss_in_front(self) -> bool:
        """Checks if there is an abyss in front of the hero."""
        return _call(self._client, _is_abyss_in_front_api.sync_detailed, default=False)

    def is_torch_in_front(self) -> bool:
        """Checks if there is a torch in front of the hero."""
        return _call(self._client, _is_torch_in_front_api.sync_detailed, default=False)

    def is_at_goal(self) -> bool:
        """Checks if the hero stands on the goal field. Some levels also need
           win conditions (e.g. all sweets collected): see Game.get_statistics()."""
        return _call(self._client, _is_at_goal_api.sync_detailed, default=False)

    def get_items_at_position(self) -> list[str]:
        """Returns the items at the hero's current position."""
        return _call(self._client, _get_items_at_position_api.sync_detailed, default=[])

    def get_inventory(self) -> list[str]:
        """Returns the list of items in the hero's inventory."""
        return _call(self._client, _get_inventory_api.sync_detailed, default=[])

    def read_item_value(self) -> int | None:
        """Returns the value of the item on the hero's field, e.g. a crystal's weight,
           or None if no item with a value lies there. Values are never shown on screen."""
        return _call(self._client, _read_item_value_api.sync_detailed, default=None)

    def peek_item_value(self, distance: int) -> int | None:
        """Returns the value of the item `distance` fields ahead in the direction the
           hero faces (1 = the field in front), or None if there is none. Only works in
           levels that have a Fernrohr (telescope)."""
        if type(distance) != int or distance < 1:
            print("Error: distance must be a whole number of at least 1.")
            return None
        return _call(self._client, _peek_item_value_api.sync_detailed, default=None,
                     explain_refusal=True, body=DistanceParam(distance=distance))

    def pickup(self, name: str) -> bool:
        """Picks up the item with provided name. Use get_items_at_position()
           to check what can be picked up at the current location."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to pickup.")
            return False
        return _call(self._client, _pickup_api.sync_detailed, default=False, body=NameParam(name=name),
                     explain_refusal="The inventory is full")

    def drop(self, name: str) -> bool:
        """Drops the item with provided name. Use get_inventory()
           to check what can be dropped."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to drop.")
            return False
        return _call(self._client, _drop_api.sync_detailed, default=False, body=NameParam(name=name))

    def set_pace(self, factor: float) -> bool:
        """Sets the hero's speed: 1 is normal, 2 twice as fast, 0.5 half as fast."""
        if type(factor) != float and type(factor) != int:
            print("Error: Factor has to be of type 'int' or 'float'.")
            return False
        if factor <= 0:
            print("Error: Factor has to be greater than 0.")
            return False
        ok = _call(self._client, _set_pace_api.sync_detailed, default=False, body=PaceParams(factor=factor))
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

    def __init__(self, level_file):
        self.__level = self.Level(self.BASE_URL)
        try:
            loaded = self.__level.load(level_file)
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
        if not loaded:
            print(f"Error: Level '{level_file}' could not be loaded. Did you start Dungeon Coder "
                  f"(\"Dungeon Coder: Enter the dungeon\")?")
            sys.exit(1)

        self.__hero = Hero(self.BASE_URL)

    @classmethod
    def generate(cls, seed: int, kind: str = "maze", **options) -> "Game":
        """Loads a generated level; the same seed always gives the same level.

        Example: Game.generate(seed=7, width=21, height=15, loops=3, fog="dark")
        kind "maze": width and height odd (default 15x11), loops = extra openings
        (cycles and free-standing walls); other keywords become map properties.
        The map text is available as generator.maze_text(seed, ...)."""
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

    def get_statistics(self) -> dict:
        """Counters of the current level since it was loaded, e.g.
        {"moves": 12, "turns": 5, "bumps": 1, "keyboard_moves": 0, "interactions": 2,
         "pickups": 0, "drops": 0, "sensor_calls": 30, "at_goal": False,
         "level_complete": False, "missing": ["3 sweets"]}.
        "missing" lists the level's win conditions that are not met yet."""
        result = _call(self.__level._client, _get_statistics_api.sync_detailed, default=None)
        return result.to_dict() if result is not None else {}

    class Level:
        """
        A class to manage game levels.
        """
        def __init__(self, base_url):
            self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))

        def load(self, filename):
            """
            Loads a level from a Tiled JSON file, or builds it from an ASCII map
            (a file ending in .txt, see asciimap.py for the format).

            Args:
                filename (str): The path to the level file.
            """
            if not os.path.exists(filename):
                raise FileNotFoundError(filename)

            if filename.endswith(".txt"):
                level_data = asciimap.level_from_file(filename)
            else:
                with open(filename, 'r') as f:
                    level_data = json.load(f)

            return _call(self._client, _load_level_api.sync_detailed, default=False,
                         body=TiledLevel.from_dict(level_data))

        def reset(self):
            """Resets the current level."""
            return _call(self._client, _reset_level_api.sync_detailed, default=False)
