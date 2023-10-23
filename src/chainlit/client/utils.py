from typing import Dict, Optional

from fastapi import Request
from starlette.datastructures import Headers

from chainlit.client.base import BaseAuthClient, BaseDBClient, UserDict
from chainlit.client.cloud import CloudAuthClient, CloudDBClient
from chainlit.client.local import LocalAuthClient, LocalDBClient
from chainlit.config import config


async def get_auth_client(
    handshake_headers: Optional[Dict[str, str]] = None,
    request_headers: Optional[Headers] = None,
) -> BaseAuthClient:
    auth_client: Optional[BaseAuthClient] = None
    if config.code.auth_client_factory:
        auth_client = await config.code.auth_client_factory(
            handshake_headers, request_headers
        )
    elif not config.project.public and config.project.id:
        # Create the auth cloud client
        auth_client = CloudAuthClient(
            project_id=config.project.id,
            handshake_headers=handshake_headers,
            request_headers=request_headers,
        )

    if auth_client:
        # Check if the user is a member of the project
        is_project_member = await auth_client.is_project_member()
        if not is_project_member:
            raise ConnectionRefusedError("User is not a member of the project")

        return auth_client

    # Default to local auth client
    return LocalAuthClient()


async def get_db_client(
    handshake_headers: Optional[Dict[str, str]] = None,
    request_headers: Optional[Headers] = None,
    user_infos: Optional[UserDict] = None,
) -> BaseDBClient:
    # Create the database client
    if config.project.database == "cloud":
        if config.project.id:
            return CloudDBClient(
                project_id=config.project.id,
                handshake_headers=handshake_headers,
                request_headers=request_headers,
            )
        else:
            raise ValueError("Project id is required for database mode 'cloud'")

    elif config.project.database == "custom":
        if config.code.db_client_factory:
            return await config.code.db_client_factory(
                handshake_headers, request_headers, user_infos
            )
        else:
            raise ValueError("Db client factory not provided")

    elif config.project.database == "local":
        return LocalDBClient(user_infos=user_infos)
    raise ValueError("Unknown database type")


async def get_auth_client_from_request(
    request: Request,
) -> BaseAuthClient:
    return await get_auth_client(None, request.headers)


async def get_db_client_from_request(
    request: Request,
) -> BaseDBClient:
    # Get the auth client
    auth_client = await get_auth_client(None, request.headers)

    return await get_db_client(None, request.headers, auth_client.user_infos)
