import sys
import csv
import requests
import httpx
import re
import base64
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# --- Functional Finder Core ---

def make_absolute_url(base_url: str, logo_url: str) -> str:
    """Ensures a logo URL is absolute."""
    if logo_url and not urlparse(logo_url).netloc:
        # Handle protocol-relative URLs like //static.facebook.com/...
        if logo_url.startswith("//"):
            return "https:" + logo_url
        return urljoin(base_url, logo_url)
    return logo_url

def find_explicit_logos(soup: BeautifulSoup, base_url: str) -> str | None:
    """HIGHEST PRIORITY: Find elements explicitly labeled as logos."""
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src", "")
        if not src:
            continue
            
        # Check for explicit logo indicators
        element_id = img.get("id", "").lower()
        element_class = ' '.join(img.get("class", [])).lower()
        alt_text = img.get("alt", "").lower()
        title_text = img.get("title", "").lower()
        
        # If any attribute explicitly mentions "logo", this is high priority
        if any("logo" in attr for attr in [src.lower(), element_id, element_class, alt_text, title_text]):
            logging.info(f"Found explicit logo: {src}")
            return make_absolute_url(base_url, src)
    
    return None

def find_logo_in_src_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """HIGH PRIORITY: Find images with 'logo' in their URL path."""
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src", "")
        if src and "logo" in src.lower():
            logging.info(f"Found logo in URL: {src}")
            return make_absolute_url(base_url, src)
    
    return None

def find_logo_by_id_class(soup: BeautifulSoup, base_url: str) -> str | None:
    """MEDIUM PRIORITY: Find images with logo-related IDs or classes."""
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src", "")
        if not src:
            continue
            
        element_id = img.get("id", "").lower()
        element_class = ' '.join(img.get("class", [])).lower()
        
        # Look for logo-related identifiers
        if any(keyword in element_id or keyword in element_class 
               for keyword in ["logo", "brand", "icon"]):
            logging.info(f"Found logo by ID/class: {src}")
            return make_absolute_url(base_url, src)
    
    return None

def find_logo_by_alt_title(soup: BeautifulSoup, base_url: str) -> str | None:
    """MEDIUM PRIORITY: Find images with logo-related alt text or title."""
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src", "")
        if not src:
            continue
            
        alt_text = img.get("alt", "").lower()
        title_text = img.get("title", "").lower()
        
        # Look for logo-related text
        if any(keyword in alt_text or keyword in title_text 
               for keyword in ["logo", "brand", "icon"]):
            logging.info(f"Found logo by alt/title: {src}")
            return make_absolute_url(base_url, src)
    
    return None

def find_in_meta_tags(soup: BeautifulSoup, base_url: str) -> str | None:
    """LOWER PRIORITY: Look for logo URLs in <meta> tags."""
    meta_properties = ["og:logo", "og:image", "twitter:image"]
    for prop in meta_properties:
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            url = make_absolute_url(base_url, tag["content"])
            if urlparse(url).scheme in ["http", "https"]:
                logging.info(f"Found logo in meta tags: {url}")
                return url
    return None

def find_inline_svg_logo(soup: BeautifulSoup, base_url: str) -> str | None:
    """LOWER PRIORITY: Find inline SVG logos."""
    search_pattern = r"logo|icon|brand"
    for link in soup.find_all("a"):
        attrs_string = ' '.join(map(str, link.attrs.values()))
        if re.search(search_pattern, attrs_string, re.IGNORECASE):
            svg = link.find("svg")
            if svg:
                for attr in ['class', 'style', 'aria-hidden', 'data-testid']:
                    if attr in svg.attrs:
                        del svg.attrs[attr]
                svg_str = str(svg)
                svg_base64 = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
                logging.info(f"Found inline SVG logo")
                return f"data:image/svg+xml;base64,{svg_base64}"
    return None

def find_logo_in_error_page(soup: BeautifulSoup, base_url: str) -> str | None:
    """LOWEST PRIORITY: Look for logos in error/rejection pages."""
    error_indicators = ["sorry", "error", "blocked", "access denied", "something went wrong"]
    
    page_text = soup.get_text().lower()
    is_error_page = any(indicator in page_text for indicator in error_indicators)
    
    if is_error_page:
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src", "")
            if src:
                if any(keyword in src.lower() for keyword in ["logo", "icon", "brand"]):
                    logging.info(f"Found logo in error page: {src}")
                    return make_absolute_url(base_url, src)
                
                img_id = img.get("id", "").lower()
                img_class = ' '.join(img.get("class", [])).lower()
                if any(keyword in img_id or keyword in img_class for keyword in ["logo", "icon", "brand"]):
                    logging.info(f"Found logo in error page by ID/class: {src}")
                    return make_absolute_url(base_url, src)
    
    return None

def find_css_background_logos(soup: BeautifulSoup, base_url: str) -> str | None:
    """Find logos embedded in CSS background images (like Verizon's base64 SVG)."""
    # Look for elements with logo-related classes that might have CSS background images
    logo_selectors = [
        "div[class*='logo']",
        "a[class*='logo']", 
        "span[class*='logo']",
        "div[id*='logo']",
        "a[id*='logo']"
    ]
    
    for selector in logo_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Check if this element has logo-related classes or IDs
            element_class = ' '.join(element.get("class", [])).lower()
            element_id = element.get("id", "").lower()
            
            if any(keyword in element_class or keyword in element_id 
                   for keyword in ["logo", "brand"]):
                logging.info(f"Found potential CSS logo element: {element.name} with classes: {element_class}")
                # For now, we can't extract the actual CSS background image from the HTML
                # But we can return a placeholder indicating we found a CSS logo
                return "css_background_logo_found"
    
    return None

def fetch_with_http2(url: str) -> tuple[bool, str | None, str | None]:
    """Strategy: HTTP/2 with advanced browser simulation (covers both HTTP/2 and HTTP/1.1)."""
    try:
        # Advanced browser headers that mimic real Chrome behavior
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
            http2=True,  # Will automatically fall back to HTTP/1.1 if needed
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
            headers=headers
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            
            logging.info(f"HTTP/2 Strategy: Status {response.status_code}, Size {len(response.content)} bytes")
            return True, response.text, str(response.url)
            
    except ImportError:
        logging.error("httpx not available - HTTP/2 strategy cannot be used")
        return False, None, None
    except Exception as e:
        logging.error(f"HTTP/2 Strategy failed: {type(e).__name__}: {e}")
        return False, None, None

def fetch_without_headers(url: str) -> tuple[bool, str | None, str | None]:
    """Strategy: Try without any headers (for sites that reject all headers)."""
    try:
        response = requests.get(url, timeout=(5, 15), allow_redirects=True)
        logging.info(f"No headers strategy: Status {response.status_code}, Size {len(response.content)} bytes")
        
        response.raise_for_status()
        return True, response.text, response.url
        
    except requests.RequestException as e:
        logging.error(f"No headers strategy failed: {type(e).__name__}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Error response status: {e.response.status_code}")
            logging.error(f"Error response content preview: {e.response.text[:500]}")
        return False, None, None

def find_first_logo(soup: BeautifulSoup, final_url: str, finders: list) -> str | None:
    """
    Finds the first logo URL by trying a list of finder functions.
    """
    # Create a lazy generator of potential logo URLs
    logo_urls = (finder(soup, final_url) for finder in finders)
    
    # Return the first truthy value (a valid URL) found by the generator
    return next((url for url in logo_urls if url), None)

def get_logo_with_strategies(url: str, strategies: list, finders: list) -> str:
    """
    Attempts to find a logo for a given URL using a list of strategies.
    """
    for strategy_name, strategy_func in strategies:
        try:
            logging.info(f"Trying strategy: {strategy_name}")
            success, content, final_url = strategy_func(url)
            
            if success and content:
                soup = BeautifulSoup(content, "html.parser")
                logo_url = find_first_logo(soup, final_url, finders)
                
            if logo_url:
                logging.info(f"Logo found using {strategy_name}: {logo_url}")
                return logo_url

            logging.info(f"No logo found using {strategy_name}")
            # Fall through to the next strategy
        except Exception as e:
            logging.error(f"Strategy '{strategy_name}' failed: {type(e).__name__}: {e}")
            # Fall through to the next strategy
            
    # If the loop finishes without returning, no logo was found.
    return "request_failed"


def get_logo_for_domain(domain: str, strategies: list, finders: list) -> str:
    """Tries to find a logo by checking multiple common URL patterns."""
    # Since we guarantee input format is always 'domain.com', we can just ensure it's clean
    domain = domain.strip()
    
    # URL list in priority order
    urls_to_try = [
        f"https://{domain}",           # Root domain (highest priority)
        f"https://about.{domain}",     # About subdomain
        f"https://{domain}/about",     # About page on root domain
    ]
    
    # Try each URL until we find a logo
    for url in urls_to_try:
        result = get_logo_with_strategies(url, strategies, finders)
        if result and result not in ["logo_not_found", "request_failed"]:
            return result

    return "logo_not_found"


def main():
    """
    Main function to read domains from STDIN and write CSV to STDOUT.
    """
    logging.basicConfig(
        level=logging.CRITICAL, format="%(levelname)s: %(message)s", stream=sys.stderr
        # level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
    
    strategies = [
        ("HTTP/2 with advanced browser simulation", fetch_with_http2),
        ("No headers fallback", fetch_without_headers),
    ]
    
    finders = [
        # find_explicit_logos,
        # find_logo_in_src_url,
        # find_logo_by_id_class,
        # find_logo_by_alt_title,
        # find_in_meta_tags,
        find_inline_svg_logo,
        # find_logo_in_error_page,
        # find_css_background_logos,
    ]
    
    writer = csv.writer(sys.stdout)
    writer.writerow(["domain", "logo_url"])

    for line in sys.stdin:
        domain = line.strip()
        if domain:
            logo_url = get_logo_for_domain(domain, strategies, finders)
            writer.writerow([domain, logo_url])


if __name__ == "__main__":
    main()