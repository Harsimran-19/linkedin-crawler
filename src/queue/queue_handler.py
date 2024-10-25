import aio_pika
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class QueueHandler:
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.queue = None
        self.processed_urls = set()

    async def connect(self):
        """Establish connection to RabbitMQ"""
        if not self.connection:
            try:
                self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
                self.channel = await self.connection.channel()
                self.queue = await self.channel.declare_queue(
                    "linkedin_urls",
                    durable=True
                )
                logger.info("Successfully connected to RabbitMQ")
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
                raise

    async def push_url(self, url: str) -> bool:
        """Push a URL to the queue if not already processed"""
        if not self.channel:
            await self.connect()

        try:
            # Normalize URL
            normalized_url = self._normalize_url(url)
            
            # Check if URL was already processed
            if normalized_url in self.processed_urls:
                return False

            # Add URL to queue
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=normalized_url.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="linkedin_urls"
            )
            
            self.processed_urls.add(normalized_url)
            logger.debug(f"Successfully pushed URL to queue: {normalized_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to push URL to queue: {str(e)}")
            return False

    async def get_url(self) -> Optional[str]:
        """Get a URL from the queue"""
        if not self.channel:
            await self.connect()

        try:
            # Get message from queue with 5 second timeout
            message = await self.queue.get(timeout=5)
            if message:
                async with message.process():
                    url = message.body.decode()
                    logger.debug(f"Retrieved URL from queue: {url}")
                    return url
            return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to get URL from queue: {str(e)}")
            return None

    def _normalize_url(self, url: str) -> str:
        """Normalize LinkedIn profile URLs"""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return f"https://www.linkedin.com{path}"

    async def close(self):
        """Close the RabbitMQ connection"""
        if self.connection:
            try:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {str(e)}")