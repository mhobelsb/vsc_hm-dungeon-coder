from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="Statistics")



@_attrs_define
class Statistics:
    """ Counters since the level was (re)loaded.

        Attributes:
            moves (int): successful move() steps
            turns (int): turn_left() turns
            bumps (int): move() calls that were blocked
            keyboard_moves (int): steps made by hand (WASD)
            interactions (int): interact() calls
            pickups (int): successful pickup() calls
            drops (int): successful drop() calls
            sensor_calls (int): calls of is_*_in_front, is_facing_north, is_at_goal and get_items_at_position
            reads (int): calls of read_item_value and peek_item_value
            questions (int): calls of ask_oracle
            at_goal (bool): the hero stands on the goal field
            game_over (bool): the hero fell into an abyss or was caught by a guard
            level_complete (bool): goal reached and every win condition of the level met
            missing (list[str]): unmet win conditions, e.g. "3 sweets"
            moves_left (int | None | Unset): move() calls left in a level with the map property max_moves (null without a
                budget)
            heroes (int | Unset): number of heroes in the level (co-op levels have more than one)
     """

    moves: int
    turns: int
    bumps: int
    keyboard_moves: int
    interactions: int
    pickups: int
    drops: int
    sensor_calls: int
    reads: int
    questions: int
    at_goal: bool
    game_over: bool
    level_complete: bool
    missing: list[str]
    moves_left: int | None | Unset = UNSET
    heroes: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        moves = self.moves

        turns = self.turns

        bumps = self.bumps

        keyboard_moves = self.keyboard_moves

        interactions = self.interactions

        pickups = self.pickups

        drops = self.drops

        sensor_calls = self.sensor_calls

        reads = self.reads

        questions = self.questions

        at_goal = self.at_goal

        game_over = self.game_over

        level_complete = self.level_complete

        missing = self.missing



        moves_left: int | None | Unset
        if isinstance(self.moves_left, Unset):
            moves_left = UNSET
        else:
            moves_left = self.moves_left

        heroes = self.heroes


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "moves": moves,
            "turns": turns,
            "bumps": bumps,
            "keyboard_moves": keyboard_moves,
            "interactions": interactions,
            "pickups": pickups,
            "drops": drops,
            "sensor_calls": sensor_calls,
            "reads": reads,
            "questions": questions,
            "at_goal": at_goal,
            "game_over": game_over,
            "level_complete": level_complete,
            "missing": missing,
        })
        if moves_left is not UNSET:
            field_dict["moves_left"] = moves_left
        if heroes is not UNSET:
            field_dict["heroes"] = heroes

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        moves = d.pop("moves")

        turns = d.pop("turns")

        bumps = d.pop("bumps")

        keyboard_moves = d.pop("keyboard_moves")

        interactions = d.pop("interactions")

        pickups = d.pop("pickups")

        drops = d.pop("drops")

        sensor_calls = d.pop("sensor_calls")

        reads = d.pop("reads")

        questions = d.pop("questions")

        at_goal = d.pop("at_goal")

        game_over = d.pop("game_over")

        level_complete = d.pop("level_complete")

        missing = cast(list[str], d.pop("missing"))


        def _parse_moves_left(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        moves_left = _parse_moves_left(d.pop("moves_left", UNSET))


        heroes = d.pop("heroes", UNSET)

        statistics = cls(
            moves=moves,
            turns=turns,
            bumps=bumps,
            keyboard_moves=keyboard_moves,
            interactions=interactions,
            pickups=pickups,
            drops=drops,
            sensor_calls=sensor_calls,
            reads=reads,
            questions=questions,
            at_goal=at_goal,
            game_over=game_over,
            level_complete=level_complete,
            missing=missing,
            moves_left=moves_left,
            heroes=heroes,
        )


        statistics.additional_properties = d
        return statistics

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
