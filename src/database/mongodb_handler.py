# src/database/mongodb_handler.py
import logging
from typing import Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self, mongodb_url: str = "mongodb://localhost:27017"):
        self.client = AsyncIOMotorClient(mongodb_url)
        self.db = self.client.linkedin_crawler
        self.posts = self.db.posts
        self.profiles = self.db.profiles

    async def store_posts(self, posts_data: List[Dict[str, Any]]) -> bool:
        """Store multiple posts in the database"""
        try:
            if not posts_data:
                return False

            # Add timestamp and process status
            for post in posts_data:
                post['crawled_at'] = datetime.utcnow()
                post['processed'] = False

            # Insert posts
            result = await self.posts.insert_many(posts_data)
            logger.info(f"Successfully stored {len(result.inserted_ids)} posts")
            return True

        except Exception as e:
            logger.error(f"Failed to store posts: {str(e)}")
            return False

    async def get_post_count(self) -> int:
        """Get total number of posts in the database"""
        try:
            return await self.posts.count_documents({})
        except Exception as e:
            logger.error(f"Failed to get post count: {str(e)}")
            return 0

    async def get_basic_metrics(self) -> Dict[str, Any]:
        """Get basic metrics about stored posts"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_posts": {"$sum": 1},
                        "avg_likes": {"$avg": "$likes_count"},
                        "avg_comments": {"$avg": "$comments_count"},
                        "media_distribution": {
                            "$push": "$media_type"
                        }
                    }
                }
            ]
            
            result = await self.posts.aggregate(pipeline).to_list(1)
            if result:
                metrics = result[0]
                # Calculate media type distribution
                media_types = metrics.pop("media_distribution", [])
                media_count = {
                    "text": media_types.count("text"),
                    "image": media_types.count("image"),
                    "video": media_types.count("video")
                }
                metrics["media_distribution"] = media_count
                return metrics
            return {}

        except Exception as e:
            logger.error(f"Failed to get basic metrics: {str(e)}")
            return {}

    async def close(self):
        """Close the MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")