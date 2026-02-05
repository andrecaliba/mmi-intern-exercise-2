import json

priority_map = {
    "high": 1,
    "medium": 2,
    "low": 3
}

# def __parse_json(filename):
#     """
#     Load and parse articles from JSON file.
    
#     Returns:
#         dict: Parsed JSON data or empty list if error occurs
#     """
#     try:
#         with open(filename, 'r') as file:
#             data = json.load(file)
#             return data
#     except FileNotFoundError:
#         print("File not found")
#         return []
#     except json.JSONDecodeError:
#         print("Invalid JSON format")
#         return []

def __publish_article(data):
    """
    Push single article to Redis sorted set.
    
    Args:
        data: Article dictionary containing url, source, category, priority
    """
    message = json.dumps(data)
    priority = data.get('priority', 'medium')
    score = priority_map.get(priority, 2)
    self.redis_client.zadd('articles', {message: score})

def publish_all(data):
    """Parse JSON file and publish all articles to Redis queue."""
    for article in data['articles']:
        __publish_article(article)