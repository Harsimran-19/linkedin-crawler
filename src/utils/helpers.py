import logging
from typing import Dict, Any
import json
from datetime import datetime

def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('crawler.log')
        ]
    )

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse LinkedIn timestamp formats"""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return datetime.utcnow()

def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data before storing in MongoDB"""
    def sanitize_value(value):
        if isinstance(value, (str, int, float, bool, datetime)):
            return value
        elif isinstance(value, dict):
            return sanitize_data(value)
        elif isinstance(value, (list, tuple)):
            return [sanitize_value(v) for v in value]
        else:
            return str(value)

    return {key: sanitize_value(value) for key, value in data.items()}