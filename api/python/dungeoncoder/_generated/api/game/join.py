from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_error_response import ApiErrorResponse
from ...models.join_params import JoinParams
from ...models.join_result import JoinResult
from typing import cast



def _get_kwargs(
    *,
    body: JoinParams,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/game/join",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ApiErrorResponse | JoinResult | None:
    if response.status_code == 200:
        response_200 = JoinResult.from_dict(response.json())



        return response_200

    if response.status_code == 500:
        response_500 = ApiErrorResponse.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ApiErrorResponse | JoinResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: JoinParams,

) -> Response[ApiErrorResponse | JoinResult]:
    """ Join a live game (an arena, map property `arena`) with a team code (map property `codes`); the
    answer names the hero and whether the game has started.

    Args:
        body (JoinParams):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | JoinResult]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    body: JoinParams,

) -> ApiErrorResponse | JoinResult | None:
    """ Join a live game (an arena, map property `arena`) with a team code (map property `codes`); the
    answer names the hero and whether the game has started.

    Args:
        body (JoinParams):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | JoinResult
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: JoinParams,

) -> Response[ApiErrorResponse | JoinResult]:
    """ Join a live game (an arena, map property `arena`) with a team code (map property `codes`); the
    answer names the hero and whether the game has started.

    Args:
        body (JoinParams):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiErrorResponse | JoinResult]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: JoinParams,

) -> ApiErrorResponse | JoinResult | None:
    """ Join a live game (an arena, map property `arena`) with a team code (map property `codes`); the
    answer names the hero and whether the game has started.

    Args:
        body (JoinParams):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiErrorResponse | JoinResult
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
