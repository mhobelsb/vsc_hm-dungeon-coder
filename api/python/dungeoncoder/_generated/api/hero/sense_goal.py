from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_error_response import ApiErrorResponse
from ...models.nullable_integer_result import NullableIntegerResult
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
        "url": "/hero/sense_goal",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ApiErrorResponse | NullableIntegerResult | None:
    if response.status_code == 200:
        response_200 = NullableIntegerResult.from_dict(response.json())



        return response_200

    if response.status_code == 500:
        response_500 = ApiErrorResponse.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ApiErrorResponse | NullableIntegerResult]:
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

) -> Response[ApiErrorResponse | NullableIntegerResult]:
    """ The amulet - how many fields the goal is away as the crow flies (columns plus rows, walls not
    counted). Needs the map property `amulett`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | NullableIntegerResult]
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

) -> ApiErrorResponse | NullableIntegerResult | None:
    """ The amulet - how many fields the goal is away as the crow flies (columns plus rows, walls not
    counted). Needs the map property `amulett`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | NullableIntegerResult
     """


    return sync_detailed(
        client=client,
hero=hero,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    hero: int | Unset = UNSET,

) -> Response[ApiErrorResponse | NullableIntegerResult]:
    """ The amulet - how many fields the goal is away as the crow flies (columns plus rows, walls not
    counted). Needs the map property `amulett`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | NullableIntegerResult]
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

) -> ApiErrorResponse | NullableIntegerResult | None:
    """ The amulet - how many fields the goal is away as the crow flies (columns plus rows, walls not
    counted). Needs the map property `amulett`.

    Args:
        hero (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | NullableIntegerResult
     """


    return (await asyncio_detailed(
        client=client,
hero=hero,

    )).parsed
