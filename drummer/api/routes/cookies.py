from typing import Annotated

from fastapi import APIRouter, Depends

from drummer.api.deps import get_cookie_jar
from drummer.core.cookies import CookieJar

router = APIRouter()

CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]


@router.get("/cookies")
async def list_cookies_route(cookie_jar: CookieJarDep) -> dict[str, dict[str, str]]:
    return cookie_jar.all_cookies()


@router.delete("/cookies")
async def clear_cookies_route(cookie_jar: CookieJarDep) -> dict[str, str]:
    cookie_jar.clear()
    return {"status": "cleared"}
