from duckduckgo_search import DDGS
import asyncio

async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Performs a web search using DuckDuckGo.
    This is entirely free, requires NO API KEY, and bypasses standard scrape blocks.
    
    Runs synchronously inside the library, so we wrap it in asyncio.to_thread 
    to prevent blocking our async orchestration engine loop.
    """
    def _sync_search():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
            
    try:
        results = await asyncio.to_thread(_sync_search)
        return results
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]
