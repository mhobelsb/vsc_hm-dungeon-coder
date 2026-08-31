from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.string_array_result_status import StringArrayResultStatus
from typing import cast






T = TypeVar("T", bound="StringArrayResult")



@_attrs_define
class StringArrayResult:
    """ 
        Attributes:
            status (StringArrayResultStatus):
            message (str):
            result (list[str]):
     """

    status: StringArrayResultStatus
    message: str
    result: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        status = self.status.value

        message = self.message

        result = self.result




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "status": status,
            "message": message,
            "result": result,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = StringArrayResultStatus(d.pop("status"))




        message = d.pop("message")

        result = cast(list[str], d.pop("result"))


        string_array_result = cls(
            status=status,
            message=message,
            result=result,
        )


        string_array_result.additional_properties = d
        return string_array_result

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
