from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib.parse
import logging


def make_absolute_url(base_url: str, logo_url: str) -> str:
    """Ensures a logo URL is absolute."""
    if not logo_url:
        return logo_url
    
    if logo_url.startswith("//"):
        return "https:" + logo_url
    
    if not urlparse(logo_url).netloc:
        return urljoin(base_url, logo_url)
    
    return logo_url


def find_svg_logos(soup: BeautifulSoup, _: str) -> str | None:
    """Find inline SVG logos and convert to data URLs."""
    def is_logo_svg(svg) -> bool:
        """Check if SVG element has logo in its class."""
        svg_class = ' '.join(svg.get("class", [])).lower()
        return "logo" in svg_class
    
    def create_svg_data_url(svg) -> str:
        """Convert SVG element to data URL."""
        svg_content = ' '.join(str(svg).split())
        return f"data:image/svg+xml,{urllib.parse.quote(svg_content)}"
    
    def process_container(container) -> str | None:
        """Process a single container for SVG logos."""
        svgs = container.find_all("svg")
        for svg in svgs:
            if is_logo_svg(svg):
                data_url = create_svg_data_url(svg)
                logging.info(f"Found SVG logo: {data_url[:100]}... (matched pattern: container with logo class + svg with logo class)")
                return data_url
        return None
    
    # Look for a and div elements with "logo" in their class
    logo_containers = soup.find_all(["a", "div"], class_=lambda x: x and "logo" in x.lower())
    
    for container in logo_containers:
        result = process_container(container)
        if result:
            return result
    
    return None


def find_navbar_brand_logos(soup: BeautifulSoup, base_url: str) -> str | None:
    """Find logos in navbar-brand links with logo in alt text."""

    def find_logo_in_link(link) -> str | None:
        """Find logo image within a single link."""
        imgs = link.find_all("img")
        for img in imgs:
            alt_text = img.get("alt", "").lower()
            if "logo" in alt_text:
                src = img.get("data-src") or img.get("src", "")
                if src:
                    return src
        return None
    
    # Look for a tags with "logo" or "brand" in their class
    brand_links = soup.find_all("a", class_=lambda x: x and any(word in x.lower() for word in ["logo", "brand"]))
    
    for link in brand_links:
        logo_src = find_logo_in_link(link)
        if logo_src:
            logging.info(f"Found navbar brand logo: {logo_src} (matched pattern: a with logo/brand class + img with logo in alt)")
            return make_absolute_url(base_url, logo_src)
    
    return None


def find_explicit_logos(soup: BeautifulSoup, base_url: str) -> str | None:
    """Find elements explicitly labeled as logos."""

    def is_logo_img(img) -> bool:
        """Check if image element is explicitly labeled as a logo."""
        src = img.get("data-src") or img.get("src", "")
        if not src:
            return False
        
        element_class = ' '.join(img.get("class", [])).lower()
        return "logo" in src.lower() or "logo" in element_class
    
    def get_logo_src(img) -> str:
        """Get the source URL from an image element."""
        return img.get("data-src") or img.get("src", "")
    
    for img in soup.find_all("img"):
        if is_logo_img(img):
            src = get_logo_src(img)
            element_class = ' '.join(img.get("class", [])).lower()
            
            if "logo" in src.lower():
                logging.info(f"Found explicit logo: {src} (matched in src URL)")
            else:
                logging.info(f"Found explicit logo: {src} (matched in class: '{element_class}')")
            
            return make_absolute_url(base_url, src)
    
    return None


def find_in_meta_tags(soup: BeautifulSoup, base_url: str) -> str | None:
    """Look for logo URLs in <meta> tags."""
    # Only check og:image since that's the only one actually used
    tag = soup.find("meta", property="og:image")
    if tag and tag.get("content"):
        url = make_absolute_url(base_url, tag["content"])
        if urlparse(url).scheme in ["http", "https"]:
            logging.info(f"Found logo in meta tags: {url} (matched property: 'og:image')")
            return url
    return None


def find_css_background_logos(soup: BeautifulSoup, _: str) -> str | None:
    """Find logos embedded in CSS background images."""
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


# Export all finders in priority order
ALL_FINDERS = [
    find_svg_logos,
    find_navbar_brand_logos,
    find_explicit_logos,
    find_in_meta_tags,
    find_css_background_logos,
]
