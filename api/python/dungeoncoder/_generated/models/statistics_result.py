from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.statistics_result_status import StatisticsResultStatus
from typing import cast

if TYPE_CHECKING:
  from ..models.statistics import Statistics





T = TypeVar("T", bound="StatisticsResult")



@_attrs_define
class StatisticsResult:
    """ 
        Attributes:
            status (StatisticsResultStatus):
            message (str):
            result (Statistics): Counters since the level was (re)loaded.
     """

    status: StatisticsResultStatus
    message: str
    result: Statistics
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.statistics import Statistics
        status = self.status.value

        message = self.message

        result = self.result.to_dict()


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
        from ..models.statistics import Statistics
        d = dict(src_dict)
        status = StatisticsResultStatus(d.pop("status"))




        message = d.pop("message")

        result = Statistics.from_dict(d.pop("result"))




        statistics_result = cls(
            status=status,
            message=message,
            result=result,
        )


        statistics_result.additional_properties = d
        return statistics_result

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
