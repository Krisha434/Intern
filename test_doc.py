import os
import shutil
import sqlite3
import pytest
import json
import warnings
import time
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask
from io import BytesIO
from app import app, initialize_whoosh_index, extract_text, get_vector, allowed_file, check_file_size
from search_strategies.strategies import ContentSearchStrategy, SimilaritySearchStrategy, SearchError, SimilarityError
from whoosh.index import open_dir
from whoosh.qparser import QueryParser

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*torch.load.*weights_only=False.*')
warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*PyPDF2.*')

def init_test_db(db_path):
    """Initialize a test SQLite database."""
    print(f"Initializing test database at {db_path}")
    try:
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if not os.access(db_dir, os.W_OK):
            raise PermissionError(f"No write permission in directory {db_dir}")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                filename TEXT NOT NULL,
                vector TEXT NOT NULL
            )
        ''')
        conn.commit()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        assert c.fetchone() is not None, "Failed to create documents table in test database"
        print(f"Successfully created test database at {db_path}")
    except Exception as e:
        print(f"Error initializing test database: {e}")
        raise
    finally:
        conn.close()

def count_documents_in_index(index_dir):
    """Count documents in the Whoosh index."""
    try:
        ix = open_dir(index_dir)
        with ix.searcher() as searcher:
            query = QueryParser("doc_id", ix.schema).parse("*")
            results = searcher.search(query, limit=None)
            print(f"Documents in index {index_dir}: {[hit['doc_id'] for hit in results]}")
            return len(results)
    except Exception as e:
        print(f"Error counting documents in index {index_dir}: {e}")
        return 0

@pytest.fixture
def client(tmp_path):
    """Create and tear down a test client and environment."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    TEST_DB_PATH = str(test_dir / 'test_database.db')
    TEST_UPLOAD_FOLDER = str(test_dir / 'test_documents')
    TEST_INDEX_DIR = str(test_dir / 'test_index')

    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = TEST_UPLOAD_FOLDER
    app.config['DB_PATH'] = TEST_DB_PATH
    app.config['INDEX_DIR'] = TEST_INDEX_DIR

    os.makedirs(TEST_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEST_INDEX_DIR, exist_ok=True)
    init_test_db(TEST_DB_PATH)
    assert os.path.exists(TEST_DB_PATH)

    with app.test_client() as client:
        yield client

    time.sleep(2.0)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError as e:
            print(f"Warning: {e}. Retrying...")
            time.sleep(2.0)
            os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_UPLOAD_FOLDER):
        shutil.rmtree(TEST_UPLOAD_FOLDER)
    if os.path.exists(TEST_INDEX_DIR):
        shutil.rmtree(TEST_INDEX_DIR)

@pytest.fixture
def mock_sentence_transformer():
    """Mock the SentenceTransformer."""
    with patch('app.SentenceTransformer') as mock:
        mock_instance = MagicMock()
        mock_instance.encode.return_value = [0.1] * 384
        mock.return_value = mock_instance
        yield mock

def test_allowed_file_valid(client):
    """Test allowed_file with valid extension."""
    file = MagicMock()
    file.filename = 'test.pdf'
    file.seek = MagicMock()
    file.tell = MagicMock(return_value=1024)
    assert allowed_file(file) is True

def test_allowed_file_invalid_extension(client):
    """Test allowed_file with invalid extension."""
    file = MagicMock()
    file.filename = 'test.txt'
    assert allowed_file(file) is False

def test_check_file_size_too_large(client):
    """Test check_file_size for file exceeding size limit."""
    file = MagicMock()
    file.seek = MagicMock()
    file.tell = MagicMock(return_value=10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match=f"File size {10 * 1024 * 1024 + 1} bytes exceeds limit"):
        check_file_size(file)

def test_extract_text_markdown(client, tmp_path):
    """Test extract_text with a markdown file."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\nThis is a test.", encoding='utf-8')
    result = extract_text(str(md_file), 'md')
    assert "<h1>Test</h1>" in result
    assert "This is a test." in result

def test_upload_document_success(client, mock_sentence_transformer):
    """Test successful document upload."""
    data = {
        'file': (BytesIO(b'%PDF-1.4\n'), 'test.pdf'),
        'title': 'Test Document',
        'category': 'Test Category'
    }
    with patch('app.PyPDF2.PdfReader') as mock_pdf:
        mock_pdf.return_value.pages = [MagicMock(extract_text=MagicMock(return_value="Sample text"))]
        response = client.post('/api/documents', content_type='multipart/form-data', data=data)
    assert response.status_code == 201
    assert response.json['message'] == 'Document uploaded successfully'
    assert 'id' in response.json
    assert len(response.json['vector']) == 384

def test_upload_document_oversized(client):
    """Test upload with oversized file."""
    file = BytesIO(b'x' * (10 * 1024 * 1024 + 1))
    data = {
        'file': (file, 'test.pdf'),
        'title': 'Test Document',
        'category': 'Test Category'
    }
    response = client.post('/api/documents', content_type='multipart/form-data', data=data)
    assert response.status_code == 413
    assert response.json['error'] == f"File size exceeds limit of {10 * 1024 * 1024} bytes"

def test_get_document_from_db(client, mock_sentence_transformer):
    """Test retrieving a document from the database."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    try:
        c = conn.cursor()
        vector = json.dumps([0.1] * 384)
        c.execute('INSERT INTO documents (title, category, filename, vector) VALUES (?, ?, ?, ?)',
                  ('Test Doc', 'Test Cat', 'test.pdf', vector))
        doc_id = c.lastrowid
        conn.commit()
    finally:
        conn.close()

    with patch('app.DB_PATH', app.config['DB_PATH']):
        response = client.get(f'/api/documents/{doc_id}')
    assert response.status_code == 200
    assert response.json['title'] == 'Test Doc'
    assert response.json['category'] == 'Test Cat'
    assert response.json['filename'] == 'test.pdf'

def test_get_non_existent_document(client):
    """Test retrieving a non-existent document."""
    with patch('app.DB_PATH', app.config['DB_PATH']):
        response = client.get('/api/documents/999')
    assert response.status_code == 404
    assert response.json['error'] == 'Document not found'

def test_content_search(client):
    """Test content-based search."""
    with patch('app.INDEX_DIR', app.config['INDEX_DIR']):
        ix = initialize_whoosh_index()
        writer = ix.writer()
        writer.add_document(doc_id='1', title='Test Doc', content='Sample content', category='Test')
        writer.commit()

        num_docs = count_documents_in_index(app.config['INDEX_DIR'])
        assert num_docs == 1

        content_search = ContentSearchStrategy(ix)
        with patch('app.content_search', content_search):
            response = client.get('/api/documents/search?q=Sample&category=Test')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['id'] == '1'
    assert response.json[0]['title'] == 'Test Doc'

def test_similarity_search(client, mock_sentence_transformer):
    """Test similarity-based search."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    try:
        c = conn.cursor()
        vector1 = json.dumps([0.1] * 384)
        vector2 = json.dumps([0.05] * 384)
        c.execute('INSERT INTO documents (title, category, filename, vector) VALUES (?, ?, ?, ?)',
                  ('Doc1', 'Cat1', 'doc1.pdf', vector1))
        doc_id1 = c.lastrowid
        c.execute('INSERT INTO documents (title, category, filename, vector) VALUES (?, ?, ?, ?)',
                  ('Doc2', 'Cat2', 'doc2.pdf', vector2))
        conn.commit()
    finally:
        conn.close()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        (json.dumps([0.1] * 384),),
        None
    ]
    mock_cursor.fetchall.return_value = [
        (2, 'Doc2', 'Cat2', json.dumps([0.05] * 384))
    ]

    with patch('app.DB_PATH', app.config['DB_PATH']):
        similarity_search = SimilaritySearchStrategy(mock_conn)
        with patch('app.similarity_search', similarity_search):
            response = client.get(f'/api/documents/similar/{doc_id1}')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['title'] == 'Doc2'
    assert 'similarity' in response.json[0]