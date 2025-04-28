import re
import requests
import sys
import os
import json
from pathlib import Path
import matplotlib.pyplot as plt
from io import BytesIO
from base64 import b64encode

def load_config(config_file="config.json"):
    """Load or create the configuration file with default settings."""
    default_config = {
        "link_validation": {
            "timeout": 5,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "validate_links": True,
            "allow_redirects": True
        },
        "analysis": {
            "include_images": True,
            "include_headings": True,
            "include_links": True,
            "min_word_length": 1
        },
        "visual_report": {
            "default_output_file": "report.html",
            "chart_width": 8,
            "chart_height": 6,
            "link_colors": ["green", "red"],
            "content_color": "blue",
            "font_family": "Arial, sans-serif",
            "margin": "20px"
        }
    }
    
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found. Creating with default settings.")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Merge with defaults for missing keys
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
            else:
                for subkey in default_config[key]:
                    if subkey not in config[key]:
                        config[key][subkey] = default_config[key][subkey]
        return config
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {config_file}: {e}. Using default settings.")
        return default_config

def validate_links(links, config):
    """Validate a list of URLs and return their status."""
    if not config["link_validation"]["validate_links"]:
        return [{'url': link, 'status': 'not_checked'} for link in links]
    
    link_status = []
    headers = {'User-Agent': config["link_validation"]["user_agent"]}
    timeout = config["link_validation"]["timeout"]
    allow_redirects = config["link_validation"]["allow_redirects"]
    
    for link in links:
        status = 'broken'
        try:
            response = requests.head(link, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
            if response.status_code < 400:
                status = 'valid'
            else:
                response = requests.get(link, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
                if response.status_code < 400:
                    status = 'valid'
        except requests.RequestException:
            pass
        link_status.append({'url': link, 'status': status})
    return link_status

def analyze_markdown(file_path, config):
    """Analyze a Markdown file and return a summary."""
    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"File {file} not found")
    
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    words = len([w for w in re.findall(r'\b\w+\b', content) if len(w) >= config["analysis"]["min_word_length"]])
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE)) if config["analysis"]["include_headings"] else 0
    links = re.findall(r'\[.*?\]\((.*?)\)|https?://[^\s)]+', content) if config["analysis"]["include_links"] else []
    images = len(re.findall(r'!\[.*?\]\(.*?\)', content)) if config["analysis"]["include_images"] else 0
    link_status = validate_links(links, config) if config["analysis"]["include_links"] else []
    
    return {
        'file': str(file),
        'words': words,
        'headings': headings,
        'links': len(links),
        'images': images,
        'link_status': link_status
    }

def print_summary(report):
    """Print a concise summary report."""
    print("\n=== Summary Report ===")
    print(f"File: {report['file']}")
    print(f"Words: {report['words']}")
    print(f"Headings: {report['headings']}")
    print(f"Links: {report['links']}")
    print(f"Images: {report['images']}")
    if report['link_status']:
        print("Links Status:")
        for link in report['link_status']:
            print(f"  - {link['url']}: {link['status']}")
    print("====================")

def generate_visual_report(report, config):
    """Generate an HTML report with embedded matplotlib charts and save Content Analysis as chart.png."""
    # Prepare data for charts
    link_status_counts = {'valid': 0, 'broken': 0}
    for link in report['link_status']:
        link_status_counts[link['status']] += 1

    # Create Link Status Distribution Chart
    plt.figure(figsize=(config["visual_report"]["chart_width"], config["visual_report"]["chart_height"]))
    plt.bar(list(link_status_counts.keys()), list(link_status_counts.values()), 
            color=config["visual_report"]["link_colors"])
    plt.title('Link Status Distribution')
    plt.xlabel('Status')
    plt.ylabel('Count')
    link_status_img = BytesIO()
    plt.savefig(link_status_img, format='png', bbox_inches='tight')
    link_status_img.seek(0)
    link_status_base64 = b64encode(link_status_img.getvalue()).decode('utf-8')
    plt.close()

    # Create Content Analysis Chart and save as chart.png
    plt.figure(figsize=(config["visual_report"]["chart_width"], config["visual_report"]["chart_height"]))
    content_data = {'Words': report['words'], 'Headings': report['headings'], 'Links': report['links'], 'Images': report['images']}
    plt.bar(list(content_data.keys()), list(content_data.values()), 
            color=config["visual_report"]["content_color"])
    plt.title('Content Analysis')
    plt.xlabel('Category')
    plt.ylabel('Count')
    # Save as chart.png
    plt.savefig("chart.png", format='png', bbox_inches='tight')
    content_img = BytesIO()
    plt.savefig(content_img, format='png', bbox_inches='tight')
    content_img.seek(0)
    content_base64 = b64encode(content_img.getvalue()).decode('utf-8')
    plt.close()
    print("Chart generated: chart.png")

    # Generate HTML content with embedded charts
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Markdown Analysis Report</title>
        <style>
            body {{ font-family: {config['visual_report']['font_family']}; margin: {config['visual_report']['margin']}; }}
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

    with open(config["visual_report"]["default_output_file"], 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Visual report generated: {config['visual_report']['default_output_file']}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyzer.py <markdown-file>")
        sys.exit(1)
    config = load_config()
    report = analyze_markdown(sys.argv[1], config)
    print_summary(report)
    generate_visual_report(report, config)