from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
# from common.auth import CurrentUser, decode_access_token

def create_middlewares(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 모든 오리진 허용 (프로덕션에서는 구체적인 도메인 지정 권장)
        allow_credentials=True,
        allow_methods=["*"],  # 모든 HTTP 메서드 허용
        allow_headers=["*"],  # 모든 헤더 허용
    )