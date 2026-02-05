def get_title(url, name):
    """Fetch URL and extract page title using BeautifulSoup."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string.strip() if soup.title else None
        
        return title if title else None
    except requests.RequestException as e:
        print(f"[{name}] Error fetching {url}: {e}")
        raise
    except Exception as e:
        print(f"[{name}] Error parsing {url}: {e}")
        raise