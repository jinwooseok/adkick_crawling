import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class BaseConfig(BaseSettings):
    # ================================
    # 앱 기본 설정
    # ================================
    APP_NAME: str = Field(default="adkick", description="애플리케이션 이름")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    VERSION: str = Field(default="0.0.1", description="애플리케이션 버전")
    SECRET_KEY: str = Field(default="change-me-in-production", description="JWT 암호화 키")
    FASTAPI_PORT: int = Field(default=8000, description="FastAPI 서버 포트")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 알고리즘")
    
    # ================================
    # MySQL 설정
    # ================================
    MYSQL_DATABASE: str = Field(default="adkick_db", description="MySQL 데이터베이스명")
    MYSQL_USERNAME: str = Field(default="adkick_user", description="MySQL 사용자명")
    MYSQL_PASSWORD: str = Field(default="", description="MySQL 비밀번호")
    MYSQL_ROOT_PASSWORD: str = Field(default="", description="MySQL 루트 비밀번호")
    MYSQL_VOLUME: str = Field(default="./mysql_data", description="MySQL 볼륨 경로")
    
    # ================================
    # Redis 설정  
    # ================================
    REDIS_PASSWORD: str = Field(default="1234", description="Redis 비밀번호")
    REDIS_DB: int = Field(default=0, description="Redis 데이터베이스 번호")
    REDIS_MAX_CONNECTIONS: int = Field(default=30, description="Redis 최대 연결 수")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, description="Redis 소켓 타임아웃 (초)")
    REDIS_CONNECT_TIMEOUT: int = Field(default=5, description="Redis 연결 타임아웃 (초)")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(default=30, description="Redis 헬스체크 간격 (초)")
    REDIS_DATA_PATH: str = Field(default="./redis_data", description="Redis 데이터 경로")
    
    # ================================
    # WebSocket 설정
    # ================================
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=5000, description="WebSocket 최대 연결 수")
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, description="WebSocket ping 간격 (초)")
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10, description="WebSocket ping 타임아웃 (초)")
    WEBSOCKET_CONNECTION_TIMEOUT: int = Field(default=300, description="WebSocket 연결 타임아웃 (초)")
    
    # Naver Search OPEN API Keys
    NAVER_CLIENT_ID: str = Field(default="")
    NAVER_CLIENT_SECRET: str = Field(default="")

    # NCP Keys
    X_NCP_APIGW_API_KEY_ID: str = Field(default="")
    X_NCP_APIGW_API_KEY: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / "app/.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # 중첩 환경 변수 지원
        case_sensitive=True,        # 대소문자 구분
        extra="ignore"              # 추가 필드 무시
    )

class LocalConfig(BaseConfig):
    """로컬 환경 설정"""
    DEBUG: bool = Field(default=True, description="디버그 모드")
    
    # MySQL 포트
    MYSQL_HOST: str = Field(alias="LOCAL_MYSQL_HOST", default="localhost", description="MySQL 호스트")
    MYSQL_BINDING_PORT: int = Field(alias="LOCAL_MYSQL_BINDING_PORT", default=3306)
    MYSQL_PORT: int = Field(alias="LOCAL_MYSQL_PORT", default=3306)
    
    # Redis 포트
    REDIS_HOST: str = Field(alias="LOCAL_REDIS_HOST", default="localhost", description="Redis 호스트")
    REDIS_PORT: int = Field(alias="LOCAL_REDIS_PORT", default=6379)
    REDIS_BINDING_PORT: int = Field(alias="LOCAL_REDIS_BINDING_PORT", default=6379)
    
    # Storage 포트
    STORAGE_API_PORT: int = Field(alias="LOCAL_STORAGE_API_PORT", default=9000)
    STORAGE_CONSOLE_PORT: int = Field(alias="LOCAL_STORAGE_CONSOLE_PORT", default=9001)
    STORAGE_ENDPOINT: str = Field(alias="LOCAL_STORAGE_ENDPOINT", default="localhost", description="스토리지 엔드포인트")

class TestConfig(BaseConfig):
    """테스트 환경 설정"""
    DEBUG: bool = Field(default=True, description="디버그 모드")
    
    # MySQL 포트
    MYSQL_HOST: str = Field(alias="TEST_MYSQL_HOST", default="localhost", description="MySQL 호스트")
    MYSQL_BINDING_PORT: int = Field(alias="TEST_MYSQL_BINDING_PORT", default=3307)
    MYSQL_PORT: int = Field(alias="TEST_MYSQL_PORT", default=3306)
    
    # Redis 포트
    REDIS_HOST: str = Field(alias="TEST_REDIS_HOST", default="localhost", description="Redis 호스트")
    REDIS_PORT: int = Field(alias="TEST_REDIS_PORT", default=6380)
    REDIS_BINDING_PORT: int = Field(alias="TEST_REDIS_BINDING_PORT", default=6379)
    
    # Storage 포트
    STORAGE_API_PORT: int = Field(alias="TEST_STORAGE_API_PORT", default=9002)
    STORAGE_CONSOLE_PORT: int = Field(alias="TEST_STORAGE_CONSOLE_PORT", default=9003)
    STORAGE_ENDPOINT: str = Field(alias="TEST_STORAGE_ENDPOINT", default="localhost", description="스토리지 엔드포인트")

class ProdConfig(BaseConfig):
    """운영 환경 설정"""
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # MySQL 포트
    MYSQL_HOST: str = Field(alias="PROD_MYSQL_HOST", default="localhost", description="MySQL 호스트")
    MYSQL_BINDING_PORT: int = Field(alias="PROD_MYSQL_BINDING_PORT", default=3308)
    MYSQL_PORT: int = Field(alias="PROD_MYSQL_PORT", default=3306)
    
    # Redis 포트
    REDIS_HOST: str = Field(alias="PROD_REDIS_HOST", default="localhost", description="Redis 호스트")
    REDIS_PORT: int = Field(alias="PROD_REDIS_PORT", default=6381)
    REDIS_BINDING_PORT: int = Field(alias="PROD_REDIS_BINDING_PORT", default=6381)
    
    # Storage 포트
    STORAGE_API_PORT: int = Field(alias="PROD_STORAGE_API_PORT", default=9004)
    STORAGE_CONSOLE_PORT: int = Field(alias="PROD_STORAGE_CONSOLE_PORT", default=9005)
    STORAGE_ENDPOINT: str = Field(alias="PROD_STORAGE_ENDPOINT", default="localhost", description="스토리지 엔드포인트")

def get_settings():
    """환경에 따라 적절한 설정 클래스 반환"""
    env = os.getenv("environment", "local")
    
    if env == "test":
        return TestConfig()
    elif env == "prod":
        return ProdConfig()
    else:
        return LocalConfig()

# 전역 설정 인스턴스
settings = get_settings()