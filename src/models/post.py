from dataclasses import dataclass
from datetime import datetime

@dataclass
class Post:
    text: str
    image_url: str = None
    post_date: datetime = None
    likes_count: int = 0
    comments_count: int = 0
    profile_id: str = None