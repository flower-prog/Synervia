"""Web search tool using Tavily API.

Provides AI agents with the ability to search the web for current information.
Requires TAVILY_API_KEY environment variable.

Get your API key at: https://tavily.com
"""

from app.core.config import settings


async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> str:
    """Search the web for current information using Tavily.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1-10, default: 5).
        search_depth: Search depth - "basic" (fast) or "advanced" (thorough).

    Returns:
        Formatted string with search results including titles, URLs, and content.
    """
    try:
        from tavily import AsyncTavilyClient
    except ImportError as e:
        raise RuntimeError("Web search unavailable: tavily package not installed.") from e

    client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
    response = await client.search(
        query=query,
        max_results=min(max_results, 10),
        search_depth=search_depth,
    )

    results = response.get("results", [])
    if not results:
        return "No web results found for this query."

    formatted = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")[:500]
        formatted.append(f"[{i}] {title}\n    URL: {url}\n    {content}")

    return f'Web search results for: "{query}"\n\n' + "\n\n".join(formatted)


def web_search_sync(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> str:
    """Synchronous wrapper for web_search (for CrewAI/LangChain sync tools)."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(web_search(query, max_results, search_depth))
    finally:
        loop.close()
