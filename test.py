import pytest
from pathlib import Path
from report_generator import (
    load_config,
    validate_links,
    analyze_markdown,
    print_summary,
    generate_visual_report
)

SAMPLE_PATH = "sample.md"

@pytest.fixture
def config():
    """Load a fresh config for each test."""
    return load_config()

def test_load_config_defaults(tmp_path):
    """Test that a missing config file gets generated with defaults."""
    cfg_path = tmp_path / "config.json"
    config = load_config(str(cfg_path))
    assert isinstance(config, dict)
    assert config["link_validation"]["timeout"] == 5
    assert cfg_path.exists()

def test_validate_links_separately(config):
    """Test validate_links function with both valid and invalid URLs."""
    test_links = ["https://www.google.com", "https://nonexistent-site12345.com","https://en.wikipedia.org/wiki/Image"]
    result = validate_links(test_links, config)

    assert isinstance(result, list)
    urls = [r["url"] for r in result]
    statuses = [r["status"] for r in result]
    
    assert test_links[0] in urls
    assert test_links[1] in urls
    assert "valid" in statuses or "broken" in statuses

    for link_result in result:
        assert link_result["status"] in ["valid", "broken", "not_checked"]
        assert link_result["url"].startswith("http")

def test_analyze_markdown_full(config):
    """Test analyze_markdown with a full-featured Markdown file."""
    report = analyze_markdown(SAMPLE_PATH, config)
    
    assert report["words"] >= 40  # Expected minimum word count
    assert report["headings"] >= 3
    assert report["links"] == 3
    assert report["images"] == 1

    # Check link_status structure
    assert isinstance(report["link_status"], list)
    for item in report["link_status"]:
        assert "url" in item and "status" in item

def test_print_summary_output(capsys, config):
    """Test print_summary prints formatted content to the terminal."""
    report = analyze_markdown(SAMPLE_PATH, config)
    print_summary(report)
    captured = capsys.readouterr()

    assert "Summary Report" in captured.out
    assert f"File: {Path(SAMPLE_PATH)}" in captured.out
    assert "Words:" in captured.out
    assert "Links Status:" in captured.out

def test_generate_visual_report_output(config, tmp_path):
    """Test generate_visual_report creates output files."""
    config["visual_report"]["default_output_file"] = str(tmp_path / "output.html")
    report = analyze_markdown(SAMPLE_PATH, config)
    generate_visual_report(report, config)

    html_file = Path(config["visual_report"]["default_output_file"])
    assert html_file.exists()
    assert Path("chart.png").exists()

    # Check HTML content includes base64-encoded images
    content = html_file.read_text(encoding="utf-8")
    assert "<img src=\"data:image/png;base64," in content
    assert "Markdown Analysis Report" in content

def test_empty_markdown_file(tmp_path, config):
    """Test edge case: empty markdown file should return 0 stats."""
    empty_md = tmp_path / "empty.md"
    empty_md.write_text("", encoding="utf-8")

    report = analyze_markdown(empty_md, config)

    assert report["words"] == 0
    assert report["headings"] == 0
    assert report["links"] == 0
    assert report["images"] == 0
    assert report["link_status"] == []

def test_partial_config_loading(tmp_path):
    """Test loading a partial config file and merging with defaults."""
    partial_config_path = tmp_path / "config.json"
    partial_config_path.write_text('{"analysis": {"include_images": false}}', encoding="utf-8")

    config = load_config(str(partial_config_path))
    assert config["analysis"]["include_images"] is False
    assert "link_validation" in config
    assert config["link_validation"]["validate_links"] is True