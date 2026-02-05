from bs4 import BeautifulSoup
import time, json, requests
from datetime import datetime

from scraper import get_title

def subscribe(name):
    """Poll Redis queue indefinitely, process articles with retry/DLQ handling."""
    while True:
        try:
            result = self.redis_client.bzpopmin('articles', timeout=0)

            if result:
                queue_name, message, score = result
                article_data = json.loads(message)
                priority = article_data.get('priority', 'medium')
                
                try:
                    __insert_to_db(article_data, name, priority)
                    print(f"[{name}] Successfully processed: {article_data.get('url')}")
                    
                except Exception as e:
                    print(f"[{name}] Error processing article: {e}")
                    
                    if "retry_count" not in article_data:
                        article_data["retry_count"] = 0
                    
                    article_data["retry_count"] += 1

                    if article_data["retry_count"] >= 3:
                        self.redis_client.lpush("failed_articles", json.dumps(article_data))
                        print(f"[{name}] Moved to DLQ: {article_data.get('url')}")
                    else:
                        self.redis_client.zadd('articles', {json.dumps(article_data): score})
                        print(f"[{name}] Retry {article_data['retry_count']}/3: {article_data.get('url')}")
                    
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            print(f"[{name}] Shutting down...")
            break
        except Exception as e:
            print(f"[{name}] Critical error: {e}")
            time.sleep(5)

def __insert_to_db(article_data, worker_id, priority="unknown"):
    """Scrape title from URL and insert article metadata into MongoDB."""
    url = article_data.get('url', '')

    title = get_title(url, worker_id)
    if not title:
        raise Exception("No title was found")
        
    metadata = {
        'id': article_data.get('id'),
        'url': url,
        'title': title,
        'source': article_data.get('source', 'unknown'),
        'category': article_data.get('category', 'unknown'),
        'priority': priority,
        'processed_at': datetime.now().isoformat(),
        'processed_by': worker_id
    }
    
    result = self.mongo_client['article_db']['articles'].insert_one(metadata)
    print(f"[{worker_id}] Inserted: {result.inserted_id}")

