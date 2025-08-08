import asyncio
import json
import logging
import time
from typing import Dict, Optional, override, List
from fastapi import WebSocket, HTTPException

from app.redis_client import AsyncRedisClient, get_async_redis_client
from app.schemas.message_types import EventType
from app.config import get_settings

logger = logging.getLogger()


class RedisPubSubGateway:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RedisPubSubGateway, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # channel -> websocket
        self.connection_times: Dict[str, float] = {}  # channel -> connection_time
        self.subscription_tasks: Dict[str, asyncio.Task] = {}  # channel -> task
        self.ping_tasks: Dict[str, asyncio.Task] = {}  # channel -> ping_task
        self.redis_client: Optional[AsyncRedisClient] = None
        self.settings = get_settings()
        
    async def _get_redis_client(self) -> AsyncRedisClient:
        """Redis 클라이언트 인스턴스 가져오기"""
        if self.redis_client is None:
            self.redis_client = await get_async_redis_client()
        return self.redis_client
    
    async def connect(self, channel: str, websocket: WebSocket) -> None:
        """특정 채널에 웹소켓 연결"""
        # 연결 수 제한 확인
        if len(self.active_connections) >= self.settings.WEBSOCKET_MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="서버 연결 한도 초과")
            raise HTTPException(status_code=503, detail="WebSocket connection limit exceeded")
            
        await websocket.accept()
        self.active_connections[channel] = websocket
        self.connection_times[channel] = time.time()
        
        # 채널 구독 시작
        await self.subscribe_to_channel(channel)
        
        # heartbeat 시작
        await self._start_heartbeat(channel, websocket)
        
        logger.info(f"WebSocket connected to channel: {channel} (Total: {len(self.active_connections)})")

    async def disconnect(self, channel: str) -> None:
        """특정 채널에서 연결 해제"""
        # 웹소켓 연결 제거
        if channel in self.active_connections:
            del self.active_connections[channel]
            
        # 연결 시간 제거
        if channel in self.connection_times:
            del self.connection_times[channel]
            
        # heartbeat 작업 종료
        if channel in self.ping_tasks:
            task = self.ping_tasks[channel]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.ping_tasks[channel]
            
        # 구독 작업 종료
        if channel in self.subscription_tasks:
            task = self.subscription_tasks[channel]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.subscription_tasks[channel]
            
        logger.info(f"Disconnected from channel: {channel} (Remaining: {len(self.active_connections)})")

    async def publish_to_channel(self, channel: str, message: dict) -> None:
        """특정 채널에 메시지 발행"""
        redis_client = await self._get_redis_client()
        # ApiResponse 구조로 블래핑
        response_data = {
            "status": 200,
            "message": "Success",
            "data": message,
            "error": None
        }
        await redis_client.publish(channel, json.dumps(response_data))
        logger.info(f"Published message to channel {channel}")

    async def publish_to_multiple_channels(self, channels: List[str], message: dict) -> None:
        """여러 채널에 메시지 발행"""
        redis_client = await self._get_redis_client()
        
        # ApiResponse 구조로 블래핑
        response_data = {
            "status": 200,
            "message": "Success",
            "data": message,
            "error": None
        }
        
        # 병렬로 모든 채널에 발행
        tasks = [
            redis_client.publish(channel, json.dumps(response_data))
            for channel in channels
        ]
        await asyncio.gather(*tasks)
        logger.info(f"Published message to {len(channels)} channels")

    async def subscribe_to_channel(self, channel: str) -> None:
        """특정 채널 구독"""
        logger.info(f"subscribe_to_channel called for channel: {channel}")
        logger.info(f"Current subscription_tasks: {list(self.subscription_tasks.keys())}")
        
        if channel in self.subscription_tasks:
            logger.info(f"Already subscribed to channel: {channel}")
            return
            
        logger.info(f"Subscribing to channel: {channel}")
        redis_client = await self._get_redis_client()
        subscriber = await redis_client.subscribe(channel)
        
        # 구독 작업 시작
        task = asyncio.create_task(self._pubsub_data_reader(channel, subscriber))
        self.subscription_tasks[channel] = task

    async def _pubsub_data_reader(self, channel: str, subscriber):
        """Redis Pub/Sub 메시지 수신 및 처리"""
        try:
            async for redis_message in subscriber.listen():
                await self._handle_pubsub_message(channel, redis_message)
        except asyncio.CancelledError:
            logger.info(f"Pub/Sub subscriber for channel {channel} has been cancelled.")
            raise
        except Exception as e:
            logger.error(f"Error in pubsub data reader for channel {channel}: {e}")
            raise

    async def _handle_pubsub_message(self, channel: str, redis_message):
        """Redis Pub/Sub 메시지 처리 및 WebSocket으로 전송"""
        try:
            # Redis 메시지 구조 처리 - subscribe/unsubscribe 메시지 필터링
            message_type = redis_message.get("type")
            if not redis_message or message_type in ["subscribe", "unsubscribe", "psubscribe", "punsubscribe"]:
                return
            
            if message_type != "message":
                return
                
            logger.info(f"Received message from Redis pubsub on channel {channel}")
                
            message_data = redis_message.get("data")
            if not message_data:
                return
                
            # JSON 문자열을 파싱
            if isinstance(message_data, bytes):
                message_data = message_data.decode('utf-8')
                
            if isinstance(message_data, str):
                try:
                    message_json = json.loads(message_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message JSON: {e}")
                    return
            else:
                message_json = message_data

            # 해당 채널의 WebSocket 연결이 있는지 확인
            if channel in self.active_connections:
                websocket = self.active_connections[channel]
                try:
                    # 메시지를 WebSocket으로 전송
                    await websocket.send_text(json.dumps(message_json))
                    logger.info(f"Sent message to WebSocket on channel {channel}")
                except Exception as e:
                    logger.error(f"Failed to send message to WebSocket on channel {channel}: {e}")
                    # 연결이 끊어진 경우 정리
                    await self.disconnect(channel)
            else:
                logger.warning(f"No active WebSocket connection for channel {channel}")

        except Exception as e:
            logger.error(f"Failed to handle pubsub message for channel {channel}: {e}")
            raise

    async def _start_heartbeat(self, channel: str, websocket: WebSocket) -> None:
        """WebSocket heartbeat 시작"""
        async def heartbeat():
            try:
                while channel in self.active_connections:
                    await asyncio.sleep(self.settings.WEBSOCKET_PING_INTERVAL)
                    
                    # 연결 타임아웃 체크
                    if channel in self.connection_times:
                        connection_age = time.time() - self.connection_times[channel]
                        if connection_age > self.settings.WEBSOCKET_CONNECTION_TIMEOUT:
                            logger.info(f"Connection timeout for channel {channel}")
                            await self.disconnect(channel)
                            return
                    
                    # ping 전송
                    try:
                        await asyncio.wait_for(
                            websocket.send_text("ping"),
                            timeout=5.0
                        )
                        logger.debug(f"Ping successful for channel {channel}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Ping timeout for channel {channel}")
                        await self.disconnect(channel)
                        return
                    except Exception as e:
                        logger.error(f"Ping failed for channel {channel}: {e}")
                        await self.disconnect(channel)
                        return
                        
            except asyncio.CancelledError:
                logger.debug(f"Heartbeat cancelled for channel {channel}")
                raise
            except Exception as e:
                logger.error(f"Heartbeat error for channel {channel}: {e}")
                await self.disconnect(channel)
        
        # heartbeat 작업 시작
        task = asyncio.create_task(heartbeat())
        self.ping_tasks[channel] = task

    async def cleanup_stale_connections(self) -> None:
        """오래된 연결 정리"""
        current_time = time.time()
        stale_channels = []
        
        for channel, connection_time in self.connection_times.items():
            if current_time - connection_time > self.settings.WEBSOCKET_CONNECTION_TIMEOUT:
                stale_channels.append(channel)
        
        for channel in stale_channels:
            logger.info(f"Cleaning up stale connection: {channel}")
            await self.disconnect(channel)
            
        if stale_channels:
            logger.info(f"Cleaned up {len(stale_channels)} stale connections")

    def get_connection_stats(self) -> dict:
        """연결 통계 정보"""
        return {
            "total_connections": len(self.active_connections),
            "max_connections": self.settings.WEBSOCKET_MAX_CONNECTIONS,
            "active_channels": list(self.active_connections.keys()),
            "connection_utilization": len(self.active_connections) / self.settings.WEBSOCKET_MAX_CONNECTIONS * 100
        }