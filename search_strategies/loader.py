import os
import logging
import PyPDF2
import markdown
from docx import Document
from lxml import etree, html
from PIL import Image
import easyocr  

logger = logging.getLogger(__name__)

class LoaderError(Exception):
    """Custom exception for file loading errors."""
    pass

class PdfLoader:
    """Loader for PDF files."""
    def load(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted
                if not text.strip():
                    raise LoaderError("No text extracted from PDF")
                return text
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {str(e)}")
            raise LoaderError(f"PDF processing error: {str(e)}")

class MarkdownLoader:
    """Loader for Markdown files."""
    def load(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
                html_content = markdown.markdown(md_content)
                return html_content
        except Exception as e:
            logger.error(f"Failed to load Markdown {file_path}: {str(e)}")
            raise LoaderError(f"Markdown processing error: {str(e)}")

class SvgLoader:
    """Loader for SVG files."""
    def load(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = etree.parse(f)
                texts = tree.xpath('//text/text()')
                text = ' '.join(t.strip() for t in texts if t.strip())
                if not text:
                    raise LoaderError("No text extracted from SVG")
                return text
        except Exception as e:
            logger.error(f"Failed to load SVG {file_path}: {str(e)}")
            raise LoaderError(f"SVG processing error: {str(e)}")

class ImageLoader:
    """Loader for image files (PNG, JPG, JPEG) using EasyOCR."""
    def __init__(self):
        # Initialize EasyOCR reader for English
        self.reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=False to avoid GPU dependency

    def load(self, file_path):
        try:
            # Use EasyOCR to extract text from the image
            logger.info(f"Processing image with EasyOCR: {file_path}")
            results = self.reader.readtext(file_path)
            # Combine all detected text into a single string
            text = ' '.join([result[1] for result in results])
            if not text.strip():
                raise LoaderError("No text extracted from image")
            logger.info(f"Extracted text (first 100 chars): {text[:100]}...")
            return text
        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {str(e)}")
            raise LoaderError(f"Image processing error: {str(e)}")

class DocxLoader:
    """Loader for DOC and DOCX files."""
    def load(self, file_path):
        try:
            doc = Document(file_path)
            text = '\n'.join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
            if not text.strip():
                raise LoaderError("No text extracted from DOCX")
            return text
        except Exception as e:
            logger.error(f"Failed to load DOCX {file_path}: {str(e)}")
            raise LoaderError(f"DOCX processing error: {str(e)}")

class TextLoader:
    """Loader for plain text files."""
    def load(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                if not text.strip():
                    raise LoaderError("No text extracted from TXT")
                return text
        except Exception as e:
            logger.error(f"Failed to load TXT {file_path}: {str(e)}")
            raise LoaderError(f"TXT processing error: {str(e)}")

class HtmlLoader:
    """Loader for HTML files."""
    def load(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                doc = html.fromstring(content)
                text = ' '.join(t.strip() for t in doc.xpath('//text()') if t.strip())
                if not text:
                    raise LoaderError("No text extracted from HTML")
                return text
        except Exception as e:
            logger.error(f"Failed to load HTML {file_path}: {str(e)}")
            raise LoaderError(f"HTML processing error: {str(e)}")

class FileLoader:
    """Manages loading of different file types using specific loaders."""
    def __init__(self):
        self.loaders = {
            'pdf': PdfLoader(),
            'md': MarkdownLoader(),
            'svg': SvgLoader(),
            'png': ImageLoader(),
            'jpg': ImageLoader(),
            'jpeg': ImageLoader(),
            'doc': DocxLoader(),
            'docx': DocxLoader(),
            'txt': TextLoader(),
            'html': HtmlLoader()
        }

    def load(self, file_path, extension):
        """Load content from a file using the appropriate loader."""
        loader = self.loaders.get(extension.lower())
        if not loader:
            logger.warning(f"No loader for extension: {extension}")
            raise LoaderError(f"Unsupported file type: {extension}")
        return loader.load(file_path)