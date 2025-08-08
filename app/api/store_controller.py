import re
from fastapi import APIRouter, BackgroundTasks, Cookie, HTTPException, Query, Request
from app.application.review_application_service import ReviewApplicationService
from app.config import get_settings

import httpx

from app.schemas.api_response import ApiResponse
from app.services.jwt_token_service import JwtTokenService

router = APIRouter()
settings = get_settings()

@router.get("/stores/search")
async def get_stores(
    keyword: str = Query(..., description="검색할 키워드 (예: '정자동 카페')"),
    size: int = Query(5, ge=1, le=5, description="결과 최대 개수 (1-5)"),
    page: int = Query(1, ge=1, description="검색 페이지 (1-)"),
    sort: str = Query(
        "random",
        pattern="^(random|comment)$",
        description="정렬 방식 (random 또는 comment)"
    ),
):
    """
    return : 검색 쿼리 결과 값
    {
        "status": 200,
        "message": "ok",
        "data": {
            "stores": [
                {"name":"스타벅스 강남점"},
                {"name":"스타벅스 상무점"}
            ]
        },
        "error": null
    }
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": size, "start": page, "sort": sort}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    
    stores = [
        {"name": re.sub(r'<[^>]+>', '', item["title"])}
        for item in data.get("items", [])
    ]
    
    return ApiResponse(data=stores)
    
@router.post("/stores/analysis")
async def get_store_analysis(
    request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    1. 상호명으로 PLACE ID 검색
    2. PLACE ID로 리뷰 검색
    3. 리뷰 분석 로직 작동
    4. DB 보고서 결과 저장
    5. 반환
    
    조건 : 크롤링 과정이 오래 걸릴 것으로 추정되므로 백그라운드로 작동 및 SSE나 WEBSOCKET과 같은 비동기 통신 사용
    
    return : 로직 실행 후 단순 로직 이후 응답은 웹소켓으로. 웹소켓이 존재하는 본 서버에 이벤트를 보내 응답하도록 함.
    """
    review_service = ReviewApplicationService()

    body = await request.json()  # JSON으로 파싱
    
    member_id = body.get("websocketId")
    store_name = body.get("name")
    print(f"member_id : {member_id} name : {store_name}")
    background_tasks.add_task(
        review_service.get_reviews,
        member_id,
        store_name
    )
    
    return ApiResponse()

# @router.get("reports/{report_id}")
# async def get_report(
#     report_id: int
# ):
#     review_service = ReviewApplicationService()
#     return await review_service.get_report(report_id)