import json
import os

import httpx

from ._generated import Client
from ._generated.errors import UnexpectedStatus
from ._generated.models.api_error_response import ApiErrorResponse
from ._generated.models.configure_params import ConfigureParams
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
    pickup as _pickup_api,
    set_pace as _set_pace_api,
    turn_left as _turn_left_api,
)
from ._generated.api.level import load_level as _load_level_api, reset_level as _reset_level_api

os.environ["NO_PROXY"] = "127.0.0.1"


def _extract_message(response) -> str:
    """Best-effort extraction of the server's error message from a raw HTTP response."""
    try:
        return json.loads(response.content).get("message", "")
    except (ValueError, AttributeError):
        return ""


def _call(client: Client, sync_detailed_fn, *, default, **kwargs):
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
    BASE_URL = "http://127.0.0.1:3000"

    def __init__(self, base_url: str = BASE_URL):
        self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))

    def configure(self, name: str, typeNumber: int) -> bool:
        return _call(self._client, _configure_api.sync_detailed, default=False,
                     body=ConfigureParams(name=name, type_number=typeNumber))

    def move(self) -> bool:
        """Sends a command to move the hero forward."""
        return _call(self._client, _move_api.sync_detailed, default=False)

    def turn_left(self) -> bool:
        """Sends a command to turn the hero to the left."""
        return _call(self._client, _turn_left_api.sync_detailed, default=False)

    def interact(self) -> bool:
        """Sends a command for the hero to interact with an object."""
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
        """Checks if the hero is an abyss is in front of the hero."""
        return _call(self._client, _is_abyss_in_front_api.sync_detailed, default=False)

    def is_torch_in_front(self) -> bool:
        """Checks if there is a switch in front of the hero."""
        return _call(self._client, _is_torch_in_front_api.sync_detailed, default=False)

    def is_at_goal(self) -> bool:
        """Checks if the hero is at the goal."""
        return _call(self._client, _is_at_goal_api.sync_detailed, default=False)

    def get_items_at_position(self) -> list[str]:
        """Returns the items at the hero's current position."""
        return _call(self._client, _get_items_at_position_api.sync_detailed, default=[])

    def get_inventory(self) -> list[str]:
        """Returns the list of items in the hero's inventory."""
        return _call(self._client, _get_inventory_api.sync_detailed, default=[])

    def pickup(self, name: str) -> bool:
        """Picks up the item with provided name. Use get_items_at_position()
           to check what can be picked up at the current location."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to pickup.")
            return False
        return _call(self._client, _pickup_api.sync_detailed, default=False, body=NameParam(name=name))

    def drop(self, name: str) -> bool:
        """Drops the item with provided name. Use get_inventory()
           to check what can be dropped."""
        if type(name) != str:
            print("Error: You have to pass a single string with the item to drop.")
            return False
        return _call(self._client, _drop_api.sync_detailed, default=False, body=NameParam(name=name))

    def set_pace(self, factor: float) -> bool:
        """Sets the hero's pace depending on the factor."""
        if type(factor) != float and type(factor) != int:
            print("Error: Factor has to be of type 'int' or 'float'.")
            return False
        return _call(self._client, _set_pace_api.sync_detailed, default=False, body=PaceParams(factor=factor))


class Game:
    """
    A class to interact with the hero game API.

    Attributes:
        hero: An instance of Hero, which handles hero-related commands.
        level: An instance of Level, which handles level-related commands.
    """

    BASE_URL = "http://127.0.0.1:3000"

    def __init__(self, level_file):
        self.__level = self.Level(self.BASE_URL)
        try:
            self.__level.load(level_file)
        except:
            print(f"Error: Level {level_file} could not be loaded. Please make sure the file exists, is valid and you opened the folder correctly.")
            exit(-1)

        self.__hero = Hero(self.BASE_URL)

    def get_hero(self):
        return self.__hero

    class Level:
        """
        A class to manage game levels.
        """
        def __init__(self, base_url):
            self._client = Client(base_url=base_url, timeout=httpx.Timeout(1))

        def load(self, filename):
            """
            Loads a level from a JSON file.

            Args:
                filename (str): The path to the JSON file containing the level data.
            """
            if not os.path.exists(filename):
                raise FileExistsError

            with open(filename, 'r') as f:
                level_data = json.load(f)

            return _call(self._client, _load_level_api.sync_detailed, default=False,
                         body=TiledLevel.from_dict(level_data))

        def reset(self):
            """Resets the current level."""
            return _call(self._client, _reset_level_api.sync_detailed, default=False)
