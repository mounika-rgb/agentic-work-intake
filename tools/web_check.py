import time
import requests
from bs4 import BeautifulSoup

def run_web_check(url: str) -> dict:
    """
    Performs a bounded GET request to audit a website.
    Returns status, response time, and basic HTML meta details or connection errors.
    """
    if not url:
        return {
            "status": "FAILED",
            "error": "No URL provided for website check."
        }
        
    # Ensure scheme is present
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    start_time = time.time()
    try:
        # Bounded request with 5s timeout
        response = requests.get(url, headers=headers, timeout=5)
        response_time = round(time.time() - start_time, 3)
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title = soup.title.string.strip() if soup.title else "N/A"
        
        # Extract meta description
        meta_desc = "N/A"
        description_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if description_tag and description_tag.get("content"):
            meta_desc = description_tag["content"].strip()
            
        return {
            "status": "SUCCESS",
            "url": url,
            "status_code": response.status_code,
            "response_time_seconds": response_time,
            "page_title": title,
            "meta_description": meta_desc,
            "headers": {k: v for k, v in list(response.headers.items())[:10]}  # First 10 headers
        }
    except requests.exceptions.Timeout:
        return {
            "status": "FAILED",
            "url": url,
            "error": "Request timed out after 5.0 seconds."
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "FAILED",
            "url": url,
            "error": "Failed to connect to the server. DNS resolution failed or host is unreachable."
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "url": url,
            "error": f"An unexpected error occurred: {str(e)}"
        }
