import asyncio
import logging

from app.redis_pubsub_gateway import RedisPubSubGateway
from app.services.place_service import place_fetcher, place_parser
from app.services.reviews_service import reviews_fetch, reviews_parser

logger = logging.getLogger()

class ReviewApplicationService:
    
    def __init__(self):
        self.pubsub_gateway = RedisPubSubGateway()

    async def get_reviews(self, member_id: int, store_name: str):
        """
        순차실행하되 각 단계를 별도 스레드에서 실행하여 블로킹 방지
        """
        try:
            loop = asyncio.get_event_loop()
            
            # 1. 상호명으로 PLACE ID 검색 (블로킹 방지)
            html = await loop.run_in_executor(None, place_fetcher, store_name, False)
            
            # 2. Place ID 추출 (html이 필요하므로 순차실행)
            place_id = await loop.run_in_executor(None, place_parser, html)
            
            # 3. 리뷰 검색 (place_id가 필요하므로 순차실행)
            more_reviews = 5
            reviews_html = await loop.run_in_executor(None, reviews_fetch, place_id, more_reviews)
            
            # 4. 리뷰 파싱 (reviews_html이 필요하므로 순차실행)
            reviews = await loop.run_in_executor(None, reviews_parser, reviews_html)
            
            if not reviews:
                await self.pubsub_gateway.publish_to_channel("review_analysis",{
                    "member_id":member_id,
                    "store_name": store_name,
                    "reviews": []
                })
            
            logger.info(f"수집된 리뷰 수: {len(reviews)}")
            # 리뷰 + 장소명 + 웹소켓ID(memberId) 발송 => 받았을 시 동일한 형태로 받은 후 분석 진행.
            await self.pubsub_gateway.publish_to_channel("review_analysis", {
                "member_id":member_id,
                "store_name": store_name,
                "reviews": reviews
            })
        except Exception:
            # 실패 발송 => 받았을 시 보고서 생성 실패 웹소켓 전달 후 저장
            await self.pubsub_gateway.publish_to_channel("review_analysis",{
                "member_id":member_id,
                "store_name": store_name,
                "message": "UNKNOWN_ERROR"
            })