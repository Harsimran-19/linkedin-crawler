# src/crawler/linkedin_crawler.py
import asyncio
import logging
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from src.models.settings import settings
from src.models.post import Post
from src.queue.queue_handler import QueueHandler
from src.database.mongodb_handler import MongoDBHandler

logger = logging.getLogger(__name__)

class LinkedInCrawler:
    def __init__(self, queue_handler: QueueHandler, db_handler: MongoDBHandler):
        self.queue_handler = queue_handler
        self.db_handler = db_handler
        self.setup_driver()

    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    async def start_crawling(self, start_url: str):
        """Start the crawling process with initial URL"""
        try:
            await self.login()
            await self.queue_handler.push_url(start_url)
            await self.process_queue()
        except Exception as e:
            logger.error(f"Error in crawling process: {str(e)}")
            raise
        finally:
            self.driver.quit()

    async def process_queue(self):
        """Process URLs from the queue concurrently"""
        while True:
            url = await self.queue_handler.get_url()
            if not url:
                break

            try:
                posts_data = await self.scrape_posts(url)
                profile_urls = await self.extract_profile_urls(url)
                
                # Store the scraped posts
                await self.db_handler.store_posts(posts_data)
                
                # Add new URLs to queue
                for profile_url in profile_urls:
                    await self.queue_handler.push_url(profile_url)
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {str(e)}")

    async def scrape_posts(self, profile_url: str) -> List[Dict]:
        """Scrape posts from a LinkedIn profile"""
        self.driver.get(profile_url + "/recent-activity/shares/")
        await asyncio.sleep(3)  # Allow page to load

        posts_data = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while len(posts_data) < 500:  # Continue until we have 500 posts
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2)
            
            # Parse current page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            posts = self._extract_posts_from_page(soup)
            posts_data.extend(posts)
            
            # Check if we've reached the end
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        return posts_data

    def _extract_posts_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract post data from the current page"""
        posts = []
        post_elements = soup.find_all("div", {"class": "feed-shared-update-v2"})
        
        for post_element in post_elements:
            post_data = {
                "content": self._extract_post_content(post_element),
                "timestamp": self._extract_timestamp(post_element),
                "likes_count": self._extract_likes(post_element),
                "comments_count": self._extract_comments(post_element),
                "media_type": self._detect_media_type(post_element),
                "url": self._extract_post_url(post_element)
            }
            posts.append(post_data)
        
        return posts

    def _detect_media_type(self, post_element) -> str:
        """Detect the type of media in the post"""
        if post_element.find("video"):
            return "video"
        elif post_element.find("img"):
            return "image"
        return "text"

    async def extract_profile_urls(self, page_url: str) -> List[str]:
        """Extract profile URLs from the page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        profile_links = soup.find_all("a", href=lambda href: href and "/in/" in href)
        return [link['href'] for link in profile_links if self._is_valid_profile_url(link['href'])]

    def _is_valid_profile_url(self, url: str) -> bool:
        """Validate LinkedIn profile URLs"""
        return url.startswith('https://www.linkedin.com/in/') and len(url) > 30

    async def login(self):
        """Login to LinkedIn"""
        self.driver.get("https://www.linkedin.com/login")
        
        # Wait for username field and login
        username_elem = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_elem.send_keys(settings.LINKEDIN_USERNAME)
        
        password_elem = self.driver.find_element(By.ID, "password")
        password_elem.send_keys(settings.LINKEDIN_PASSWORD)
        
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        await asyncio.sleep(20)  # Wait for login to complete

    def _extract_post_content(self, post_element) -> str:
        """Extract the text content of a post"""
        content_div = post_element.find("div", {"class": "feed-shared-update-v2__description-wrapper"})
        return content_div.get_text(strip=True) if content_div else ""
    def _extract_timestamp(self, post_element) -> Optional[str]:
        """Extract the timestamp of a post from the LinkedIn post HTML"""
        # Locate the anchor tag containing the timestamp information
        timestamp_elem = post_element.find("a", {"class": "update-components-actor__sub-description-link"})
        
        if timestamp_elem:
            try:
                # Locate the <span> with class 'visually-hidden' that contains the timestamp
                span_elem = timestamp_elem.find("span", {"class": "visually-hidden"})
                if span_elem:
                    # Extract and return the text (e.g., "1 week ago")
                    return span_elem.get_text(strip=True)
            except (AttributeError, ValueError) as e:
                # Log error if needed and return None
                logger.error(f"Error extracting timestamp: {str(e)}")
                return None
    
        return None

    def _extract_likes(self, post_element) -> int:
        """Extract the number of likes on a post"""
        likes_elem = post_element.find("span", {"class": "social-details-social-counts__reactions-count"})
        try:
            return int(likes_elem.get_text(strip=True)) if likes_elem else 0
        except ValueError:
            return 0
    def _extract_comments(self, post_element) -> int:
        """Extract the number of comments on a post"""
        # Find the <li> element that contains the comments count
        comments_elem = post_element.find("li", {"class": "social-details-social-counts__comments"})
        
        if comments_elem:
            try:
                # Directly locate the <span> within the <button> that contains the comment count
                button_elem = comments_elem.find("button")
                if button_elem:
                    # Extract the text from the <span> inside the <button>
                    span_elem = button_elem.find("span")
                    if span_elem:
                        comment_count_text = span_elem.get_text(strip=True)
                        # Extract only the number part before "comments"
                        comment_count = int(comment_count_text.split()[0])
                        return comment_count
            except (AttributeError, ValueError) as e:
                # Log the error if needed and return 0
                logger.error(f"Error extracting comment count: {str(e)}")
                return 0
    
        return 0


    def _extract_post_url(self, post_element) -> Optional[str]:
        """Extract the URL of the post"""
        link_elem = post_element.find("a", {"class": "feed-shared-update-v2__permalink"})
        return link_elem.get('href') if link_elem else None