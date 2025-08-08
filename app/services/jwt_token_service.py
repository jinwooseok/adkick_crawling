from datetime import datetime, timedelta, timezone
from jose import jwt


from app.config import get_settings

settings = get_settings()
class JwtTokenService:
    """JWT를 사용한 토큰 서비스 구현체"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
    
    def create_token(self, payload: dict, expires_delta: timedelta) -> str:
        expire = datetime.now(timezone.utc) + expires_delta
        payload.update({"exp": expire})
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])