"""Serves the built SvelteKit SPA (adapter-static) from the Web process.

A path that names a file in the build directory gets that file. Every other page path gets the
SPA fallback page `200.html`, so the browser router can show the page. Paths under /api/ and /ws/
never get the fallback page.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

SPA_FALLBACK_PAGE = "200.html"
BACKEND_PATH_PREFIXES = ("api/", "ws/")
# Cloudflare does not change a response with no-transform: it does not inject the Web Analytics script into
# the pages (docs/architecture.md section 14).
FRONTEND_FILE_HEADERS = {"Cache-Control": "no-transform"}


def find_build_file(build_dir: Path, requested_path: str) -> Path | None:
    resolved_build_dir = build_dir.resolve()
    candidate = (resolved_build_dir / requested_path).resolve()
    if not candidate.is_relative_to(resolved_build_dir):
        return None
    if not candidate.is_file():
        return None
    return candidate


def create_frontend_router(build_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/{requested_path:path}", include_in_schema=False)
    async def read_frontend_file(requested_path: str) -> FileResponse:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        if requested_path.startswith(BACKEND_PATH_PREFIXES):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        build_file = find_build_file(build_dir, requested_path)
        if build_file is None:
            return FileResponse(build_dir / SPA_FALLBACK_PAGE, headers=FRONTEND_FILE_HEADERS)
        return FileResponse(build_file, headers=FRONTEND_FILE_HEADERS)

    return router
