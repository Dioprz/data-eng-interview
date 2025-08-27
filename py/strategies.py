import httpx
import requests
import logging

HTTP2_TIMEOUT = 10.0
HTTP2_CONNECT_TIMEOUT = 5.0
FALLBACK_CONNECT_TIMEOUT = 5
FALLBACK_READ_TIMEOUT = 15
ERROR_CONTENT_PREVIEW_LENGTH = 500


def fetch_with_http2(url: str) -> tuple[bool, str | None, str | None]:
    """Strategy: HTTP/2 with browser simulation (covers both HTTP/2 and HTTP/1.1)."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Cache-Control": "max-age=0",
        }
        
        # HTTP/2 request with automatic fallback to HTTP/1.1
        with httpx.Client(
            http2=True,
            timeout=httpx.Timeout(HTTP2_TIMEOUT, connect=HTTP2_CONNECT_TIMEOUT),
            follow_redirects=True,
            headers=headers
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            
            logging.info(f"HTTP/2 Strategy: Status {response.status_code}, Size {len(response.content)} bytes")
            return True, response.text, str(response.url)
            
    except Exception as e:
        logging.error(f"HTTP/2 Strategy failed: {type(e).__name__}: {e}")
        return False, None, None


def fetch_without_headers(url: str) -> tuple[bool, str | None, str | None]:
    """Strategy: Try without any headers (for sites that reject all headers)."""
    try:
        response = requests.get(url, timeout=(FALLBACK_CONNECT_TIMEOUT, FALLBACK_READ_TIMEOUT), allow_redirects=True)
        logging.info(f"No headers strategy: Status {response.status_code}, Size {len(response.content)} bytes")
        
        response.raise_for_status()
        return True, response.text, response.url
        
    except requests.RequestException as e:
        logging.error(f"No headers strategy failed: {type(e).__name__}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Error response status: {e.response.status_code}")
            logging.error(f"Error response content preview: {e.response.text[:ERROR_CONTENT_PREVIEW_LENGTH]}")
        return False, None, None


# Strategies in priority order
ALL_STRATEGIES = [
    ("HTTP/2 with browser simulation", fetch_with_http2),
    ("No headers fallback", fetch_without_headers),
]
