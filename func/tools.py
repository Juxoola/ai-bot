import asyncio
import logging
from typing import Iterator
from urllib.parse import urlparse
from aiohttp import ClientError, ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from ddgs import DDGS

def scrape_text(html: str, max_words: int = None, add_source=True, count_images: int = 2) -> Iterator[str]:
    source = BeautifulSoup(html, "html.parser")
    soup = source
    for selector in [
            "main",
            ".main-content-wrapper",
            ".main-content",
            ".emt-container-inner",
            ".content-wrapper",
            "#content",
            "#mainContent",
        ]:
        select = soup.select_one(selector)
        if select:
            soup = select
            break
    for remove in [".c-globalDisclosure"]:
        select = soup.select_one(remove)
        if select:
            select.extract()

    image_select = "img[alt][src^=http]:not([alt=''])"
    image_link_select = f"a:has({image_select})"
    yield_words = []
    for paragraph in soup.select(f"h1, h2, h3, h4, h5, h6, p, table:not(:has(p)), ul:not(:has(p)), {image_link_select}"):
        if count_images > 0:
            image = paragraph.select_one(image_select)
            if image:
                title = paragraph.get("title") or paragraph.text
                if title:
                    yield f"!{title}({image['src']})\n" 
                    if max_words is not None:
                        max_words -= 10
                    count_images -= 1
                continue

        for line in paragraph.text.splitlines():
            words = [word for word in line.split() if word]
            count = len(words)
            if not count:
                continue
            words = " ".join(words)
            if words in yield_words:
                continue
            if max_words:
                max_words -= count
                if max_words <= 0:
                    break
            yield words + "\n"
            yield_words.append(words)

    if add_source:
        canonical_link = source.find("link", rel="canonical")
        if canonical_link and "href" in canonical_link.attrs:
            link = canonical_link["href"]
            domain = urlparse(link).netloc
            yield f"\nSource: [{domain}]({link})"

async def fetch_and_scrape(session: ClientSession, url: str, max_words: int = None, add_source: bool = False) -> str:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                text = "".join(scrape_text(html, max_words, add_source))
                return text
    except (ClientError, asyncio.TimeoutError):
        return

class SearchResultEntry():
    def __init__(self, title: str, url: str, snippet: str, text: str=None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.text = text

async def search_tool(query: str, max_results: int = 3, max_words: int = 1500, backend: str = "auto", region: str = "wt-wt", timeout: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(
                    query,
                    region=region,
                    safesearch="moderate",
                    timelimit="y",
                    max_results=max_results,
                    backend="bing",
                ):
                if ".google." in result["href"]:
                    continue
                results.append(SearchResultEntry(
                    result["title"],
                    result["href"],
                    result["body"]
                ))

            requests = []
            async with ClientSession(timeout=ClientTimeout(timeout)) as session:
                for entry in results:
                    requests.append(fetch_and_scrape(session, entry.url, int(max_words / max_results), False))
                texts = await asyncio.gather(*requests)

            formatted_results = []
            for i, entry in enumerate(results):
                entry.text = texts[i]
                formatted_results.append(
                    f"[{i}] Title: {entry.title}\n"
                    f"Text: {entry.text if entry.text else entry.snippet}\n"
                    f"URL: {entry.url}\n"
                )
            return "\n".join(formatted_results)
    except Exception as e:
        logging.error(f"Error in search_tool: {e}")
        return f"An error occurred during the search: {e}"