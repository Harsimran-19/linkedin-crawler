#!/bin/bash
# entrypoint.sh

# Check if URL argument is provided
if [ -z "$1" ]; then
    echo "Error: Please provide a LinkedIn URL to crawl"
    echo "Usage: docker run -e LINKEDIN_USERNAME=your_username -e LINKEDIN_PASSWORD=your_password your-image your_linkedin_url"
    exit 1
fi

# Run the crawler with the provided URL
python main.py "$1"