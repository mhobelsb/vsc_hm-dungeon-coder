from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.api_error_response_status import ApiErrorResponseStatus
from ..types import UNSET, Unset






T = TypeVar("T", bound="ApiErrorResponse")



@_attrs_define
class ApiErrorResponse:
    """ 
        Attributes:
            status (ApiErrorResponseStatus):
            message (str):
            exception (str | Unset):
     """

    status: ApiErrorResponseStatus
    message: str
    exception: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        status = self.status.value

        message = self.message

        exception = self.exception


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "status": status,
            "message": message,
        })
        if exception is not UNSET:
            field_dict["exception"] = exception

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = ApiErrorResponseStatus(d.pop("status"))




        message = d.pop("message")

        exception = d.pop("exception", UNSET)

        api_error_response = cls(
            status=status,
            message=message,
            exception=exception,
        )


        api_error_response.additional_properties = d
        return api_error_response

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
