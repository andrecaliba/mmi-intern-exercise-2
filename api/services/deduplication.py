from database.connection import DatabaseManager
from database.repositories.article_repo import ArticleRepository
from api.models.article import ArticleStatus

async def get_article_repo():
    await DatabaseManager.connect()
    db = DatabaseManager.get_database()
    return ArticleRepository(db)

async def query_url(url: str):
    article_repo = await get_article_repo()
    return await article_repo.get_by_url(url)

async def exist_and_is_scraped(url: str):
    article_repo = await get_article_repo()
    doc = await article_repo.get_by_url(url)
    if doc and doc.status == ArticleStatus.SCRAPED:
        return True
    return False