from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.version_result import VersionResult
from typing import cast



def _get_kwargs(
    
) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/version",
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> VersionResult | None:
    if response.status_code == 200:
        response_200 = VersionResult.from_dict(response.json())



        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[VersionResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,

) -> Response[VersionResult]:
    """ The versions of the extension and of this API, so a client can tell whether it fits.

     Answered by the server itself (x-host), not by the game. The Python
    package compares it with its own version once per program and warns if
    a copied package doesn't fit the running extension.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[VersionResult]
     """


    kwargs = _get_kwargs(
        
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,

) -> VersionResult | None:
    """ The versions of the extension and of this API, so a client can tell whether it fits.

     Answered by the server itself (x-host), not by the game. The Python
    package compares it with its own version once per program and warns if
    a copied package doesn't fit the running extension.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        VersionResult
     """


    return sync_detailed(
        client=client,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,

) -> Response[VersionResult]:
    """ The versions of the extension and of this API, so a client can tell whether it fits.

     Answered by the server itself (x-host), not by the game. The Python
    package compares it with its own version once per program and warns if
    a copied package doesn't fit the running extension.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[VersionResult]
     """


    kwargs = _get_kwargs(
        
    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,

) -> VersionResult | None:
    """ The versions of the extension and of this API, so a client can tell whether it fits.

     Answered by the server itself (x-host), not by the game. The Python
    package compares it with its own version once per program and warns if
    a copied package doesn't fit the running extension.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        VersionResult
     """


    return (await asyncio_detailed(
        client=client,

    )).parsed
