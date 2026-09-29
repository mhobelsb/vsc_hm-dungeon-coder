from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.nullable_string_result_status import NullableStringResultStatus
from typing import cast






T = TypeVar("T", bound="NullableStringResult")



@_attrs_define
class NullableStringResult:
    """ 
        Attributes:
            status (NullableStringResultStatus):
            message (str):
            result (None | str):
     """

    status: NullableStringResultStatus
    message: str
    result: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        status = self.status.value

        message = self.message

        result: None | str
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
        status = NullableStringResultStatus(d.pop("status"))




        message = d.pop("message")

        def _parse_result(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        result = _parse_result(d.pop("result"))


        nullable_string_result = cls(
            status=status,
            message=message,
            result=result,
        )


        nullable_string_result.additional_properties = d
        return nullable_string_result

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
