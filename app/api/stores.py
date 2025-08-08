from typing import Union
from fastapi import APIRouter, HTTPException, Query
import httpx
from app.config import get_settings
from app.schemas.store import StoreSearchResponse, SimpleStoreResponse

router = APIRouter()
settings = get_settings()
@router.get(
    "/stores",
    response_model=Union[StoreSearchResponse, SimpleStoreResponse],
    summary="네이버플레이스 검색",
)
async def get_stores(
    query: str = Query(..., description="검색할 키워드 (예: '정자동 카페')"),
    display: int = Query(5, ge=1, le=5, description="결과 최대 개수 (1-5)"),
    start: int = Query(1, ge=1, description="검색 페이지 (1-)"),
    sort: str = Query(
        "random",
        pattern="^(random|comment)$",
        description="정렬 방식 (random 또는 comment)"
    ),
    simple: bool = Query(False, description="상호명, 위도, 경도만 반환"),
):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": start, "sort": sort}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()

    # Simple Response 활성화 시
    if simple:
        simple_items = [
            {"title": item["title"], "mapx": item["mapx"], "mapy": item["mapy"]}
            for item in data.get("items", [])
        ]
        return SimpleStoreResponse(items=simple_items)

    return StoreSearchResponse(**data)
