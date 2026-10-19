from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="JoinInfo")



@_attrs_define
class JoinInfo:
    """ 
        Attributes:
            hero (int): the index of the hero the code controls (query parameter hero)
            name (str): the team's name, the part of the code before the dash
            started (bool): the referee has started the game
            heroes (int): how many heroes (teams) the level has
     """

    hero: int
    name: str
    started: bool
    heroes: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        hero = self.hero

        name = self.name

        started = self.started

        heroes = self.heroes


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "hero": hero,
            "name": name,
            "started": started,
            "heroes": heroes,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        hero = d.pop("hero")

        name = d.pop("name")

        started = d.pop("started")

        heroes = d.pop("heroes")

        join_info = cls(
            hero=hero,
            name=name,
            started=started,
            heroes=heroes,
        )


        join_info.additional_properties = d
        return join_info

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
