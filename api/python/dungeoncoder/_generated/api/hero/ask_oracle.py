from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_error_response import ApiErrorResponse
from ...models.nullable_string_result import NullableStringResult
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    hero: int | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["hero"] = hero


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/hero/ask_oracle",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ApiErrorResponse | NullableStringResult | None:
    if response.status_code == 200:
        response_200 = NullableStringResult.from_dict(response.json())



        return response_200

    if response.status_code == 500:
        response_500 = ApiErrorResponse.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ApiErrorResponse | NullableStringResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    hero: int | Unset = UNSET,

) -> Response[ApiErrorResponse | NullableStringResult]:
    r""" The oracle's advice, the first step of a shortest way to the exit (\"north\", \"east\", \"south\" or
    \"west\"); null on the goal or without a way. Needs the map property `orakel`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | NullableStringResult]
     """


    kwargs = _get_kwargs(
        hero=hero,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    hero: int | Unset = UNSET,

) -> ApiErrorResponse | NullableStringResult | None:
    r""" The oracle's advice, the first step of a shortest way to the exit (\"north\", \"east\", \"south\" or
    \"west\"); null on the goal or without a way. Needs the map property `orakel`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | NullableStringResult
     """


    return sync_detailed(
        client=client,
hero=hero,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    hero: int | Unset = UNSET,

) -> Response[ApiErrorResponse | NullableStringResult]:
    r""" The oracle's advice, the first step of a shortest way to the exit (\"north\", \"east\", \"south\" or
    \"west\"); null on the goal or without a way. Needs the map property `orakel`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | NullableStringResult]
     """


    kwargs = _get_kwargs(
        hero=hero,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    hero: int | Unset = UNSET,

) -> ApiErrorResponse | NullableStringResult | None:
    r""" The oracle's advice, the first step of a shortest way to the exit (\"north\", \"east\", \"south\" or
    \"west\"); null on the goal or without a way. Needs the map property `orakel`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | NullableStringResult
     """


    return (await asyncio_detailed(
        client=client,
hero=hero,

    )).parsed
