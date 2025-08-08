import json
import logging
from typing import Any, Dict, Optional, Union, List
from datetime import timedelta

import redis.asyncio as aioredis
from redis.asyncio import client
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.config import BaseConfig, get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AsyncRedisClient:
    """비동기 Redis 클라이언트 래퍼 클래스"""
    
    def __init__(self, settings):
        self.settings = settings
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None
        self.redis_url = f"redis://:{self.settings.REDIS_PASSWORD}@{self.settings.REDIS_HOST}:{self.settings.REDIS_BINDING_PORT}"
        self._pubsub_instances: Dict[str, client.PubSub] = {}
        # logger.info(f"REDIS_HOST: {self.settings.REDIS_HOST}")
        # logger.info(f"REDIS_BINDING_PORT: {self.settings.REDIS_BINDING_PORT}")
        # logger.info(f"REDIS_PASSWORD: {'***' if self.settings.REDIS_PASSWORD else 'None'}")
        # logger.info(f"REDIS_SOCKET_TIMEOUT: {self.settings.REDIS_SOCKET_TIMEOUT}")
        # logger.info(f"REDIS_CONNECT_TIMEOUT: {self.settings.REDIS_CONNECT_TIMEOUT}")
    
    async def _initialize_client(self):
        """Redis 클라이언트 초기화"""
        try:
            # Connection Pool 생성
            self._pool = ConnectionPool(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_BINDING_PORT,
                password=self.settings.REDIS_PASSWORD,
                db=self.settings.REDIS_DB,
                decode_responses=True,
                max_connections=self.settings.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=True,
                socket_timeout=self.settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=self.settings.REDIS_CONNECT_TIMEOUT,
                health_check_interval=self.settings.REDIS_HEALTH_CHECK_INTERVAL,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Redis 클라이언트 생성
            self._client = aioredis.Redis(connection_pool=self._pool)
            # 연결 테스트
            await self._client.ping()
            logger.info("Async Redis 연결 성공")
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Async Redis 연결 실패: {e}")
            raise e
    
    async def get_client(self) -> aioredis.Redis:
        """Redis 클라이언트 반환 (비동기)"""
        if self._client is None:
            await self._initialize_client()
        
        if self._client is None:
            raise RedisError("Failed to initialize Redis client")
        
        return self._client
    
    async def get_pubsub_for_channel(self, channel: str) -> client.PubSub:
        """채널별 PubSub 인스턴스 반환 (비동기)"""
        if channel not in self._pubsub_instances:
            client = await self.get_client()
            self._pubsub_instances[channel] = client.pubsub()
        
        return self._pubsub_instances[channel]
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ex: Optional[Union[int, timedelta]] = None,
        px: Optional[Union[int, timedelta]] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        키-값 저장 (비동기)
        
        Args:
            key: Redis 키
            value: 저장할 값 (자동으로 JSON 직렬화)
            ex: 만료 시간 (초 또는 timedelta)
            px: 만료 시간 (밀리초 또는 timedelta)
            nx: 키가 존재하지 않을 때만 설정
            xx: 키가 존재할 때만 설정
        """
        try:
            client = await self.get_client()
            # 값이 문자열이 아니면 JSON으로 직렬화
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return bool(result) if result is not None else False
            
        except RedisError as e:
            logger.error(f"Redis SET 오류 - key: {key}, error: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        키로 값 조회 (비동기)
        
        Args:
            key: Redis 키
            
        Returns:
            저장된 값 (JSON이면 자동으로 파싱)
        """
        try:
            client = await self.get_client()
            value = await client.get(key)
            
            if value is None:
                return None
            
            # JSON 파싱 시도
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아니면 원본 문자열 반환
                return value
                
        except RedisError as e:
            logger.error(f"Redis GET 오류 - key: {key}, error: {e}")
            return None
    
    async def delete(self, *keys: str) -> int:
        """키 삭제 (비동기)"""
        try:
            client = await self.get_client()
            result = await client.delete(*keys)
            return int(result) if result is not None else 0
        except RedisError as e:
            logger.error(f"Redis DELETE 오류 - keys: {keys}, error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인 (비동기)"""
        try:
            client = await self.get_client()
            result = await client.exists(key)
            return bool(result) if result is not None else False
        except RedisError as e:
            logger.error(f"Redis EXISTS 오류 - key: {key}, error: {e}")
            return False
    
    async def expire(self, key: str, time: Union[int, timedelta]) -> bool:
        """키 만료 시간 설정 (비동기)"""
        try:
            client = await self.get_client()
            result = await client.expire(key, time)
            return bool(result) if result is not None else False
        except RedisError as e:
            logger.error(f"Redis EXPIRE 오류 - key: {key}, error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """키의 남은 TTL 조회 (초) (비동기)"""
        try:
            client = await self.get_client()
            result = await client.ttl(key)
            return int(result) if result is not None else -1
        except RedisError as e:
            logger.error(f"Redis TTL 오류 - key: {key}, error: {e}")
            return -1
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """키 값 증가 (비동기)"""
        try:
            client = await self.get_client()
            result = await client.incr(key, amount)
            return int(result) if result is not None else 0
        except RedisError as e:
            logger.error(f"Redis INCR 오류 - key: {key}, error: {e}")
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """키 값 감소 (비동기)"""
        try:
            client = await self.get_client()
            result = await client.decr(key, amount)
            return int(result) if result is not None else 0
        except RedisError as e:
            logger.error(f"Redis DECR 오류 - key: {key}, error: {e}")
            return 0
    
    async def flushdb(self) -> bool:
        """현재 DB의 모든 키 삭제 (비동기) - 개발용"""
        try:
            client = await self.get_client()
            result = await client.flushdb()
            return bool(result) if result is not None else False
        except RedisError as e:
            logger.error(f"Redis FLUSHDB 오류: {e}")
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """패턴에 매칭되는 키 조회 (비동기) - 주의: 운영에서는 사용 금지"""
        try:
            client = await self.get_client()
            result = await client.keys(pattern)
            return list(result) if result else []
        except RedisError as e:
            logger.error(f"Redis KEYS 오류 - pattern: {pattern}, error: {e}")
            return []
    
    async def close(self):
        """연결 종료 (비동기)"""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        for pubsub in self._pubsub_instances.values():
            await pubsub.close()
        self._pubsub_instances.clear()
        logger.info("Async Redis 연결 종료")

    async def publish(self, topic: str, message) -> None:
        """
        Publishes a message to a specific Redis channel.

        Args:
            topic (str): Channel or room ID.
            message (str): Message to be published.
        """
        logger.info(f"topic being published to {topic}")
        client = await self.get_client()
        print(topic)
        await client.publish(topic, message)

    async def subscribe(self, topic: str) -> client.PubSub:
            """
            Subscribes to a Redis channel.

            Args:
                topic (str): Channel or room ID to subscribe to.

            Returns:
                aioredis.client.PubSub: PubSub object for the subscribed channel.
            """
            pubsub = await self.get_pubsub_for_channel(topic)
            await pubsub.subscribe(topic)
            return pubsub

    async def unsubscribe(self, topic: str) -> None:
        """
        Unsubscribes from a Redis channel.

        Args:
            topic (str): Channel or room ID to unsubscribe from.
        """
        if topic in self._pubsub_instances:
            pubsub = self._pubsub_instances[topic]
            await pubsub.unsubscribe(topic)
            await pubsub.close()
            del self._pubsub_instances[topic]

    async def listen(self, topic: str) -> None:
        """
        Listens for messages on the subscribed channel.
        """
        pubsub = await self.get_pubsub_for_channel(topic)
        async for message in pubsub.listen():
            if message["type"] == "message":
                print(f"Received message: {message['data']}")


# 싱글톤 인스턴스
_async_redis_client: Optional[AsyncRedisClient] = None


async def get_async_redis_client() -> AsyncRedisClient:
    """비동기 Redis 클라이언트 싱글톤 인스턴스 반환"""
    global _async_redis_client
    
    if _async_redis_client is None:
        _async_redis_client = AsyncRedisClient(settings)
    
    return _async_redis_client


async def close_async_redis_client():
    """비동기 Redis 클라이언트 연결 종료"""
    global _async_redis_client
    
    if _async_redis_client:
        await _async_redis_client.close()
        _async_redis_client = None