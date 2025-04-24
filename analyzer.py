import re
import requests
import sys
from pathlib import Path

def validate_links(links: list) -> list:
    """Validate a list of URLs and return their status
       Returns:
        list: List of dictionaries containing each URL and its status ('valid' or 'broken')."""
    link_status = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    for link in links:
        status = 'broken'
        try:
            # First try HEAD request
            response = requests.head(link, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                status = 'valid'
            else:
                # Fallback to GET if HEAD fails
                response = requests.get(link, headers=headers, timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    status = 'valid'
        except requests.RequestException:
            pass  # Keep status as 'broken' if all requests fail
        link_status.append({'url': link, 'status': status})
    return link_status

def analyze_markdown(file_path: str) -> dict:
    """Analyze a Markdown file and return a summary."""
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"File {file} not found")
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count words
    words = len(re.findall(r'\b\w+\b', content))

    # Count headings (lines starting with #)
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))

    # Count links (Markdown [text](url) and raw URLs)
    links = re.findall(r'\[.*?\]\((.*?)\)|https?://[^\s)]+', content)
    link_count = len(links)

    # Count images (Markdown ![text](url))
    images = len(re.findall(r'!\[.*?\]\(.*?\)', content))

    # Validate links using the separate function
    link_status = validate_links(links)

    return {
        'file': str(file),
        'words': words,
        'headings': headings,
        'links': link_count,
        'images': images,
        'link_status': link_status
    }

def print_summary(report: dict) -> None:
    """Print a concise summary report."""
    print("\n=== Summary Report ===")
    print(f"File: {report['file']}")
    print(f"Words: {report['words']}")
    print(f"Headings: {report['headings']}")
    print(f"Links: {report['links']}")
    print(f"Images: {report['images']}")
    print("Links Status:")
    for link in report['link_status']:
        print(f"  - {link['url']}: {link['status']}")
    print("====================")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyzer.py <markdown-file>")
        sys.exit(1)
    report = analyze_markdown(sys.argv[1])
    print_summary(report)