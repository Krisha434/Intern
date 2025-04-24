import re
import requests
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from io import BytesIO
from base64 import b64encode

def validate_links(links: list) -> list:
    """Validate a list of URLs and return their status."""
    link_status = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    for link in links:
        status = 'broken'
        try:
            response = requests.head(link, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                status = 'valid'
            else:
                response = requests.get(link, headers=headers, timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    status = 'valid'
        except requests.RequestException:
            pass
        link_status.append({'url': link, 'status': status})
    return link_status

def analyze_markdown(file_path: str) -> dict:
    """Analyze a Markdown file and return a summary."""
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"File {file} not found")
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    words = len(re.findall(r'\b\w+\b', content))
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))
    links = re.findall(r'\[.*?\]\((.*?)\)|https?://[^\s)]+', content)
    link_count = len(links)
    images = len(re.findall(r'!\[.*?\]\(.*?\)', content))
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

def generate_visual_report(report: dict, output_file: str = "report.html") -> None:
    """Generate an HTML report with embedded matplotlib charts."""
    # Prepare data for charts
    link_status_counts = {'valid': 0, 'broken': 0}
    for link in report['link_status']:
        link_status_counts[link['status']] += 1

    # Create Link Status Distribution Chart
    plt.figure(figsize=(8, 6))
    plt.bar(list(link_status_counts.keys()), list(link_status_counts.values()), color=['green', 'red'])
    plt.title('Link Status Distribution')
    plt.xlabel('Status')
    plt.ylabel('Count')
    link_status_img = BytesIO()
    plt.savefig(link_status_img, format='png', bbox_inches='tight')
    link_status_img.seek(0)
    link_status_base64 = b64encode(link_status_img.getvalue()).decode('utf-8')
    plt.close()

    # Create Content Analysis Chart
    plt.figure(figsize=(8, 6))
    content_data = {'Words': report['words'], 'Headings': report['headings'], 'Links': report['links'], 'Images': report['images']}
    plt.bar(list(content_data.keys()), list(content_data.values()), color='blue')
    plt.title('Content Analysis')
    plt.xlabel('Category')
    plt.ylabel('Count')
    content_img = BytesIO()
    plt.savefig(content_img, format='png', bbox_inches='tight')
    content_img.seek(0)
    content_base64 = b64encode(content_img.getvalue()).decode('utf-8')
    plt.close()

    # Generate HTML content with embedded charts
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Markdown Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3, h4 {{ color: #333; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ margin-bottom: 5px; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>Markdown Analysis Report</h1>
        <h2>File: {report['file']}</h2>
        <h3>Summary</h3>
        <ul>
            <li>Words: {report['words']}</li>
            <li>Headings: {report['headings']}</li>
            <li>Links: {report['links']}</li>
            <li>Images: {report['images']}</li>
        </ul>
        <h3>Link Status</h3>
        <ul>
        {'<li>'.join([f"{link['url']}: {link['status']}" for link in report['link_status']])}
        </ul>
        <h3>Charts</h3>
        <h4>Link Status Distribution</h4>
        <img src="data:image/png;base64,{link_status_base64}" alt="Link Status Chart">
        <h4>Content Analysis</h4>
        <img src="data:image/png;base64,{content_base64}" alt="Content Analysis Chart">
    </body>
    </html>
    """

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Visual report generated: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyzer.py <markdown-file>")
        sys.exit(1)
    report = analyze_markdown(sys.argv[1])
    print_summary(report)
    generate_visual_report(report)  # Generate HTML report with charts