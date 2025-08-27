import sys
import csv
import logging
import requests
from bs4 import BeautifulSoup
from finders import ALL_FINDERS
from strategies import ALL_STRATEGIES

LOGO_NOT_FOUND = "logo_not_found"
REQUEST_FAILED = "request_failed"
NOT_WORKING_SITE = "not_working_site"

CONNECTIVITY_TIMEOUT = 10


def check_site_connectivity(url: str) -> str | None:
    """Check if a site is reachable (DNS resolution, basic connectivity)."""
    try:
        requests.get(url, timeout=CONNECTIVITY_TIMEOUT, allow_redirects=True)
        return None
        
    except requests.exceptions.ConnectionError as e:
        error_str = str(e).lower()
        dns_errors = [
            "could not resolve host",
            "name or service not known", 
            "name resolution failed"
        ]
        
        if any(dns_error in error_str for dns_error in dns_errors):
            logging.info(f"Site appears non-functional (DNS resolution failure): {e}")
            return NOT_WORKING_SITE
        
        return None
        
    except Exception as e:
        return None


def find_first_logo(soup: BeautifulSoup, final_url: str, finders: list) -> str | None:
    """Finds the first logo URL by trying a list of finder functions."""
    logo_urls = (finder(soup, final_url) for finder in finders)
    
    # Return the first truthy value (a valid URL) found by the generator
    return next((url for url in logo_urls if url), None)


def process_strategy(strategy_name: str, strategy_func, url: str, finders: list) -> str | None:
    """Process a single strategy and return logo if found."""
    try:
        logging.info(f"Trying strategy: {strategy_name}")
        success, content, final_url = strategy_func(url)
        
        if not success or not content:
            return None
        
        soup = BeautifulSoup(content, "html.parser")
        return find_first_logo(soup, final_url, finders)
        
    except Exception as e:
        logging.error(f"Strategy '{strategy_name}' failed: {type(e).__name__}: {e}")
        return None


def get_logo_with_strategies(url: str, strategies: list, finders: list) -> str:
    """Attempts to find a logo for a given URL using a list of strategies."""
    for strategy_name, strategy_func in strategies:
        logo_url = process_strategy(strategy_name, strategy_func, url, finders)
        if logo_url:
            logging.info(f"Logo found using {strategy_name}: {logo_url}")
            return logo_url
    
    return REQUEST_FAILED


def generate_domain_urls(domain: str) -> list[str]:
    """Generate URLs to try for a domain in priority order."""
    return [
        f"https://{domain}",           # Root domain (highest priority)
        f"https://about.{domain}",     # About subdomain
        f"https://{domain}/about",     # About page on root domain
    ]


def get_logo_for_domain(domain: str, strategies: list, finders: list) -> str:
    """Tries to find a logo by checking multiple common URL patterns."""
    domain = domain.strip()
    
    for url in generate_domain_urls(domain):
        result = get_logo_with_strategies(url, strategies, finders)
        if result and result not in [LOGO_NOT_FOUND, REQUEST_FAILED]:
            return result

    return LOGO_NOT_FOUND


def process_domain(domain: str) -> str:
    """Process a single domain and return the result string."""
    connectivity_result = check_site_connectivity(f"https://{domain}")
    if connectivity_result == NOT_WORKING_SITE:
        return NOT_WORKING_SITE
    
    return get_logo_for_domain(domain, ALL_STRATEGIES, ALL_FINDERS)


def print_summary(total_success: int, total_failed_or_not_found: int, total_not_working_sites: int):
    """Print final summary to stderr."""
    print(f"SUMMARY: success={total_success}, failed_or_not_found={total_failed_or_not_found}, not_working_sites={total_not_working_sites}", file=sys.stderr)


def main():
    """Main function to read domains from STDIN and write CSV to STDOUT."""
    logging.basicConfig(
        level=logging.CRITICAL, format="%(levelname)s: %(message)s", stream=sys.stderr
        # level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
    
    writer = csv.writer(sys.stdout)
    writer.writerow(["domain", "logo_url"])

    total_success = 0
    total_failed_or_not_found = 0
    total_not_working_sites = 0

    for line in sys.stdin:
        domain = line.strip()
        if domain:
            result = process_domain(domain)
            writer.writerow([domain, result])
            
            if result == NOT_WORKING_SITE:
                total_not_working_sites += 1
            elif result in (LOGO_NOT_FOUND, REQUEST_FAILED):
                total_failed_or_not_found += 1
            else:
                total_success += 1

    # print_summary(total_success, total_failed_or_not_found, total_not_working_sites)


if __name__ == "__main__":
    main()