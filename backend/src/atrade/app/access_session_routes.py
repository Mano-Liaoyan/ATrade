"""GET /api/access-session: tells the frontend if Cloudflare Access protects the page, and where to log out."""

from typing import Annotated

from fastapi import APIRouter, Header
from pydantic import BaseModel

# Cloudflare answers this path itself. It deletes the Access cookie and ends the Access session of the user in all
# Access applications (docs/architecture.md section 14).
ACCESS_LOGOUT_PATH = "/cdn-cgi/access/logout"


class AccessSessionResponse(BaseModel):
    # None when the request did not come through Cloudflare Access, for example on a development machine.
    logout_url: str | None


def create_access_session_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/access-session")
    async def read_access_session(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        cf_access_jwt_assertion: Annotated[str | None, Header()] = None,
    ) -> AccessSessionResponse:
        # Cloudflare Access adds the header to each request that it lets through. The Web process does not check the
        # token: the header only decides if the app shell shows the Log out button.
        if not cf_access_jwt_assertion:
            return AccessSessionResponse(logout_url=None)
        return AccessSessionResponse(logout_url=ACCESS_LOGOUT_PATH)

    return router
