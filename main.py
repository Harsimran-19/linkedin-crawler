# main.py
import asyncio
import logging
import argparse
from src.crawler.linkedin_crawler import LinkedInCrawler
from src.queue.queue_handler import QueueHandler
from src.database.mongodb_handler import MongoDBHandler
from src.utils.helpers import setup_logging
from src.models.settings import settings
import os

async def main(start_url: str):
    """Main function to run the LinkedIn crawler"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    worker_name = os.environ.get('WORKER_NAME', 'worker')
    logger.info(f"Starting {worker_name} with URL: {start_url}")
    
    try:
        # Initialize handlers with environment-specific connection strings
        queue_handler = QueueHandler(settings.RABBITMQ_URL)
        db_handler = MongoDBHandler(settings.MONGODB_URL)
        
        # Initialize crawler
        crawler = LinkedInCrawler(
            queue_handler=queue_handler,
            db_handler=db_handler
        )
        
        # Start crawling
        await crawler.start_crawling(start_url)
        
    except Exception as e:
        logger.error(f"Crawler failed: {str(e)}")
        raise
    finally:
        # Cleanup
        await queue_handler.close()
        await db_handler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LinkedIn Post Crawler')
    parser.add_argument('--url', required=True, help='Starting LinkedIn URL')
    args = parser.parse_args()
    
    asyncio.run(main(args.url))