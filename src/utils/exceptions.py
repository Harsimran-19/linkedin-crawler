class LinkedInCrawlerException(Exception):
    """Base exception for LinkedIn crawler"""
    pass

class LoginError(LinkedInCrawlerException):
    """Raised when login fails"""
    pass

class ScrapingError(LinkedInCrawlerException):
    """Raised when scraping fails"""
    pass

class QueueError(LinkedInCrawlerException):
    """Raised when queue operations fail"""
    pass

class DatabaseError(LinkedInCrawlerException):
    """Raised when database operations fail"""
    pass