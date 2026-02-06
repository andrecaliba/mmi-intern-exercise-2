"""
Web Scraper Module
Handles article content extraction from URLs
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple
import time


# Request configuration
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
TIMEOUT = 10  # seconds


def get_title(url: str, worker_id: str = "worker") -> Optional[str]:
    """
    Extract article title from URL.
    
    Args:
        url: Article URL
        worker_id: Worker identifier for logging
        
    Returns:
        Article title or None if not found
    """
    try:
        print(f"[{worker_id}] Fetching title from: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try multiple selectors to find title
        title = soup.title.string.strip()
        
        if title:
            print(f"[{worker_id}] Title found: {title[:50]}...")
            return title
        else:
            print(f"[{worker_id}] No title found")
            return None
            
    except requests.Timeout:
        print(f"[{worker_id}] Timeout fetching {url}")
        raise Exception("Request timeout")
    
    except requests.HTTPError as e:
        print(f"[{worker_id}] HTTP error: {e.response.status_code}")
        raise Exception(f"HTTP {e.response.status_code}")
    
    except Exception as e:
        print(f"[{worker_id}] Error extracting title: {e}")
        raise


def get_content(url: str, worker_id: str = "worker") -> Optional[str]:
    """
    Extract article content from URL.
    
    Args:
        url: Article URL
        worker_id: Worker identifier for logging
        
    Returns:
        Article content or None if not found
    """
    try:
        print(f"[{worker_id}] Fetching content from: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try multiple methods to extract content
        content = None
        
        # Method 1: <article> tag
        article_tag = soup.find('article')
        if article_tag:
            paragraphs = article_tag.find_all('p')
            if paragraphs:
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # Method 2: div with class containing 'content' or 'article'
        if not content:
            content_div = soup.find('div', class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower()))
            if content_div:
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # Method 3: All <p> tags in main content
        if not content:
            main_tag = soup.find('main')
            if main_tag:
                paragraphs = main_tag.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # Method 4: All <p> tags (fallback)
        if not content:
            paragraphs = soup.find_all('p')
            if paragraphs:
                # Filter out very short paragraphs (likely navigation/footer)
                valid_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
                if valid_paragraphs:
                    content = '\n\n'.join(valid_paragraphs)
        
        if content:
            content_preview = content[:100].replace('\n', ' ')
            print(f"[{worker_id}] Content found: {len(content)} chars - {content_preview}...")
            return content
        else:
            print(f"[{worker_id}] No content found")
            return None
            
    except requests.Timeout:
        print(f"[{worker_id}] Timeout fetching {url}")
        raise Exception("Request timeout")
    
    except requests.HTTPError as e:
        print(f"[{worker_id}] HTTP error: {e.response.status_code}")
        raise Exception(f"HTTP {e.response.status_code}")
    
    except Exception as e:
        print(f"[{worker_id}] Error extracting content: {e}")
        raise


def scrape_article(url: str, worker_id: str = "worker") -> Tuple[Optional[str], Optional[str]]:
    """
    Scrape both title and content from URL.
    
    Args:
        url: Article URL
        worker_id: Worker identifier for logging
        
    Returns:
        Tuple of (title, content)
    """
    try:
        print(f"[{worker_id}] Scraping article: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        if not title:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text().strip()
        
        # Extract content
        content = None
        article_tag = soup.find('article')
        if article_tag:
            paragraphs = article_tag.find_all('p')
            if paragraphs:
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        if not content:
            paragraphs = soup.find_all('p')
            if paragraphs:
                valid_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
                if valid_paragraphs:
                    content = '\n\n'.join(valid_paragraphs)
        
        if title and content:
            print(f"[{worker_id}] Scraped successfully: {title[:50]}... ({len(content)} chars)")
            return title, content
        else:
            raise Exception(f"Missing {'title' if not title else 'content'}")
            
    except Exception as e:
        print(f"[{worker_id}] Scraping failed: {e}")
        raise