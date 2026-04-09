import trafilatura , asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _single_article(url):
    try:

        html = await asyncio.wait_for(
                asyncio.to_thread(trafilatura.fetch_url, url), 
                timeout=10
            )
        
        if not html:
            return None, "no HTML returned (possible bot-block or empty page)"
        
        text = await asyncio.wait_for(
                asyncio.to_thread(trafilatura.extract, html), 
                timeout=10
            )
        
        if not text:
            return None, "HTML fetched but no text could be extracted"
        
        return text, None
    
    except asyncio.TimeoutError:
        logger.error("[TimeOut] Article taking too time")
        return None, "[TimeOut] Article taking too time"
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"

def _fetch_article_wrapper(url):
    return asyncio.run(_single_article(url))

def fetch_article(urls):

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_fetch_article_wrapper, urls))
    
    return results

# --- Testing ---
if __name__ == "__main__":
    url_input = []
    for i in range(2):
        url_input.append(str(input("Enter URL: ")))

    result = fetch_article(url_input)
    print(result)