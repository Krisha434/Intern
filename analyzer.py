import sys
import os
import re
import json
import requests
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Matplotlib to avoid display issues
import matplotlib.pyplot as plt
from collections import Counter
from base64 import b64encode
from io import BytesIO

# Ensure the output directory exists
OUTPUT_DIR = os.path.abspath(os.getcwd())  # Use current working directory
CHART_PATH = os.path.join(OUTPUT_DIR, "chart.png")
REPORT_PATH = os.path.join(OUTPUT_DIR, "report.html")

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
            "default_output_file": REPORT_PATH,  # Use absolute path
            "chart_width": 8,
            "chart_height": 6,
            "link_colors": ["green", "red"],
            "content_color": "blue",
            "font_family": "Arial, sans-serif",
            "margin": "20px"
        }
    }

    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found. Creating with default settings...")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created config file at {config_file}")
        except Exception as e:
            print(f"Error creating config file: {e}")
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
        print(f"Error: Invalid JSON in {config_file}: {e}. Using default settings...")
        return default_config


def validate_links(links: list, config) -> list:
    """Validate a list of URLs and return their status."""
    if not config["link_validation"]["validate_links"]:
        print("Link validation disabled in config. Skipping validation.")
        return [{'url': link, 'status': 'not_checked'} for link in links]

    link_status = []
    headers = {'User-Agent': config["link_validation"]["user_agent"]}
    timeout = config["link_validation"]["timeout"]
    allow_redirects = config["link_validation"]["allow_redirects"]

    for link in links:
        try:
            response = requests.head(link, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
            status = 'valid' if response.status_code < 400 else 'broken'
        except requests.RequestException as e:
            print(f"Error validating link {link}: {e}")
            status = 'broken'
        link_status.append({'url': link, 'status': status})

    return link_status


def analyze_markdown(file_path: str, config) -> dict:
    """Analyze a markdown file and return a report of its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError as e:
        print(f"Error: Markdown file {file_path} not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading markdown file {file_path}: {e}")
        sys.exit(1)

    words = len([w for w in re.findall(r'\b\w+\b', content) if len(w) >= config["analysis"]["min_word_length"]])
    headings = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE)) if config["analysis"]["include_headings"] else 0
    links = re.findall(r'\[.*?\]\((.*?)\)|https?://[^\s)]+', content) if config["analysis"]["include_links"] else []
    images = len(re.findall(r'!\[.*?\]\(.*?\)', content)) if config["analysis"]["include_images"] else 0
    link_status = validate_links(links, config) if config["analysis"]["include_links"] else []

    return {
        'word_count': words,
        'heading_count': headings,
        'link_count': len(links),
        'image_count': images,
        'link_status': link_status
    }


def print_summary(report: dict) -> None:
    """Print a summary of the markdown analysis."""
    print("Markdown Analysis Summary:")
    print(f"Words: {report['word_count']}")
    print(f"Headings: {report['heading_count']}")
    print(f"Links: {report['link_count']}")
    print(f"Images: {report['image_count']}")
    print("Link Status:")
    for link in report['link_status']:
        print(f"  {link['url']}: {link['status']}")


def generate_visual_report(report: dict, config) -> None:
    """Generate an HTML report with embedded matplotlib charts and save Content Analysis as chart.png."""
    print("Starting report generation...")

    # Check if report data is empty
    if not any([report['word_count'], report['heading_count'], report['link_count'], report['image_count']]):
        print("Warning: No data to visualize. Skipping report generation.")
        return

    # Prepare data for visualization
    link_status_counts = Counter(link['status'] for link in report['link_status'])
    statuses = ['valid', 'broken', 'not_checked']
    status_counts = [link_status_counts.get(status, 0) for status in statuses]

    # Create Link Status Distribution chart
    try:
        plt.figure(figsize=(config["visual_report"]["chart_width"], config["visual_report"]["chart_height"]))
        plt.bar(statuses, status_counts, color=config["visual_report"]["link_colors"] + ["gray"])
        plt.title("Link Status Distribution")
        plt.xlabel("Status")
        plt.ylabel("Count")

        # Save the chart as a base64 string for embedding
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        image_base64 = b64encode(image_png).decode('utf-8')
        link_status_chart = f'data:image/png;base64,{image_base64}'
        plt.close()
        print("Link Status chart generated and encoded as base64.")
    except Exception as e:
        print(f"Error generating Link Status chart: {e}")
        return

    # Create Content Analysis chart
    try:
        plt.figure(figsize=(config["visual_report"]["chart_width"], config["visual_report"]["chart_height"]))
        content_metrics = ['Words', 'Headings', 'Images']
        content_counts = [report['word_count'], report['heading_count'], report['image_count']]
        plt.bar(content_metrics, content_counts, color=config["visual_report"]["content_color"])
        plt.title("Content Analysis")
        plt.ylabel("Count")
        print(f"Saving Content Analysis chart with counts: {content_counts}")
        plt.savefig(CHART_PATH, format='png', bbox_inches='tight')
        plt.close()
        print(f"Content Analysis chart saved to {CHART_PATH}")
    except Exception as e:
        print(f"Error generating or saving Content Analysis chart: {e}")
        return

    # Generate HTML report
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
        <h2>Summary</h2>
        <ul>
            <li>Words: {report['word_count']}</li>
            <li>Headings: {report['heading_count']}</li>
            <li>Links: {report['link_count']}</li>
            <li>Images: {report['image_count']}</li>
        </ul>
        <h2>Link Status</h2>
        <ul>
    """

    for link in report['link_status']:
        color = 'green' if link['status'] == 'valid' else 'red' if link['status'] == 'broken' else 'gray'
        html_content += f"<li style='color: {color};'>{link['url']}: {link['status']}</li>"

    html_content += f"""
        </ul>
        <h2>Visualizations</h2>
        <h3>Link Status Distribution</h3>
        <img src="{link_status_chart}" alt="Link Status Distribution">
        <h3>Content Analysis</h3>
        <img src="file://{CHART_PATH}" alt="Content Analysis">
    </body>
    </html>
    """

    # Write the HTML report
    output_file = config["visual_report"]["default_output_file"]
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Report successfully written to {output_file}")
    except Exception as e:
        print(f"Error writing report to {output_file}: {e}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyzer.py <markdown-file>")
        sys.exit(1)

    config = load_config()
    report = analyze_markdown(sys.argv[1], config)
    print_summary(report)
    generate_visual_report(report, config)