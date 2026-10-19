from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class SensitiveBodyRoute(APIRoute):
    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        route_handler = super().get_route_handler()

        async def sanitized_route_handler(request: Request) -> Response:
            try:
                return await route_handler(request)
            except RequestValidationError as error:
                sanitized_errors = [
                    {
                        key: validation_error[key]
                        for key in ("type", "loc", "msg")
                        if key in validation_error
                    }
                    for validation_error in error.errors()
                ]
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=sanitized_errors,
                ) from None

        return sanitized_route_handler
