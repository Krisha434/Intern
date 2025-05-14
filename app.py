import os
import sqlite3
import logging
import shutil
import json
from flask import Flask, request, jsonify
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
import PyPDF2
import markdown
from sentence_transformers import SentenceTransformer
import numpy as np
import vec
from search_strategies.strategies import ContentSearchStrategy, SimilaritySearchStrategy

# Configure logging to show only basic info in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
logger.info("Starting Document Management System")

# Configuration
UPLOAD_FOLDER = 'documents'
INDEX_DIR = 'index'
DB_PATH = 'database.db'
ALLOWED_EXTENSIONS = {'pdf', 'md'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# Initialize sentence transformer for vector embeddings
logger.info("Loading sentence transformer model")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Failed to load sentence transformer model: {str(e)}")
    raise

# Whoosh schema for indexing
schema = Schema(
    doc_id=ID(stored=True, unique=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True),
    category=TEXT(stored=True)
)

def initialize_whoosh_index():
    """Initialize or recover the Whoosh search index, creating a new one if needed."""
    try:
        if os.path.exists(INDEX_DIR) and not os.listdir(INDEX_DIR):
            logger.warning("Index directory is empty. Creating a new Whoosh index.")
            return create_in(INDEX_DIR, schema)
        else:
            logger.info("Opening existing Whoosh index")
            return open_dir(INDEX_DIR)
    except Exception as e:
        logger.error(f"Failed to open Whoosh index: {str(e)}. Creating a new one.")
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
        os.makedirs(INDEX_DIR)
        return create_in(INDEX_DIR, schema)

ix = initialize_whoosh_index()

def init_db():
    """Set up the SQLite database with a table for document metadata."""
    logger.info("Setting up database")
    try:
        conn = sqlite3.connect(DB_PATH)
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
        conn.close()
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Failed to set up database: {str(e)}")
        raise

init_db()

# Initialize search strategies
conn = sqlite3.connect(DB_PATH)  # Persistent connection for search strategies
content_search = ContentSearchStrategy(ix)
similarity_search = SimilaritySearchStrategy(conn)

# Helper functions
def allowed_file(filename):
    """Check if a file has an allowed extension (pdf or md)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file_path, extension):
    """Extract text from a PDF or Markdown file."""
    try:
        if extension == 'pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ''
                return text
        elif extension == 'md':
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
                return markdown.markdown(md_content)
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {str(e)}")
        raise

def get_vector(text):
    """Generate a 384-dimensional numerical vector embedding for the given text."""
    try:
        embedding = model.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to generate vector: {str(e)}")
        raise

# API Endpoints
@app.route('/api/documents', methods=['POST'])
def upload_document():
    """Upload a new document, save it, and index it for search."""
    logger.info("Uploading new document")
    if 'file' not in request.files or 'title' not in request.form or 'category' not in request.form:
        logger.warning("Missing required fields")
        return jsonify({'error': 'Please provide file, title, and category'}), 400

    file = request.files['file']
    title = request.form['title']
    category = request.form['category']

    if not allowed_file(file.filename):
        logger.warning(f"Unsupported file type: {file.filename}")
        return jsonify({'error': 'Only PDF and Markdown files are allowed'}), 400

    extension = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{title}_{os.urandom(8).hex()}.{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        file.save(file_path)
    except Exception as e:
        logger.error(f"Failed to save file: {str(e)}")
        return jsonify({'error': 'Could not save file'}), 500

    try:
        content = extract_text(file_path, extension)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path} after failure")
        return jsonify({'error': 'Could not process file content'}), 500

    try:
        vector = get_vector(content)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path} after failure")
        return jsonify({'error': 'Could not generate document embedding'}), 500

    try:
        vector_json = json.dumps(vector)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO documents (title, category, filename, vector) VALUES (?, ?, ?, ?)',
                  (title, category, filename, vector_json))
        doc_id = c.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path} after failure")
        logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Could not save document metadata'}), 500

    try:
        writer = ix.writer()
        writer.add_document(doc_id=str(doc_id), title=title, content=content, category=category)
        writer.commit()
    except Exception as e:
        logger.error(f"Failed to index document: {str(e)}")
        return jsonify({'error': 'Could not index document'}), 500

    logger.info(f"Document uploaded: ID {doc_id}, Title: {title}")
    return jsonify({'message': 'Document uploaded successfully', 'id': doc_id, 'vector': vector}), 201

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """Retrieve metadata for a specific document by ID."""
    logger.info(f"Fetching document ID {doc_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, title, category, filename, vector FROM documents WHERE id = ?', (doc_id,))
        doc = c.fetchone()
        conn.close()

        if not doc:
            logger.warning(f"Document ID {doc_id} not found")
            return jsonify({'error': 'Document not found'}), 404

        vector = json.loads(doc[4])
        return jsonify({
            'id': doc[0],
            'title': doc[1],
            'category': doc[2],
            'filename': doc[3],
            'vector': vector
        }), 200
    except Exception as e:
        logger.error(f"Error fetching document: {str(e)}")
        return jsonify({'error': 'Could not fetch document'}), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List metadata for all documents in the database."""
    logger.info("Listing all documents")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, title, category, filename, vector FROM documents')
        docs = c.fetchall()
        conn.close()

        return jsonify([{
            'id': doc[0],
            'title': doc[1],
            'category': doc[2],
            'filename': doc[3],
            'vector': json.loads(doc[4])
        } for doc in docs]), 200
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': 'Could not list documents'}), 500

@app.route('/api/documents/search', methods=['GET'])
def search_documents():
    """Search documents by content and optionally filter by category."""
    query_str = request.args.get('q', '')
    category = request.args.get('category', '')
    logger.info(f"Searching with query: '{query_str}', category: '{category}'")

    try:
        results = content_search.search(query_str, category)
        return jsonify(results), 200
    except Exception as e:
        logger.error(str(e))
        return jsonify({'error': 'Could not perform search'}), 500

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document by ID from the database, filesystem, and index."""
    logger.info(f"Deleting document ID {doc_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT filename FROM documents WHERE id = ?', (doc_id,))
        doc = c.fetchone()
        if not doc:
            conn.close()
            logger.warning(f"Document ID {doc_id} not found")
            return jsonify({'error': 'Document not found'}), 404

        file_path = os.path.join(UPLOAD_FOLDER, doc[0])
        writer = ix.writer()
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            c.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            writer.delete_by_term('doc_id', str(doc_id))
            conn.commit()
            writer.commit()
        except Exception as e:
            conn.rollback()
            writer.cancel()
            raise
        finally:
            conn.close()

        logger.info(f"Document ID {doc_id} deleted")
        return jsonify({'message': 'Document deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': 'Could not delete document'}), 500 

@app.route('/api/documents/similar/<int:doc_id>', methods=['GET'])
def find_similar_documents(doc_id):
    """Find the top 5 documents similar to the specified document by vector similarity."""
    logger.info(f"Finding similar documents for ID {doc_id}")
    try:
        results = similarity_search.find_similar(doc_id)
        return jsonify(results), 200
    except Exception as e:
        logger.error(str(e))
        if "Document not found" in str(e):
            return jsonify({'error': 'Document not found'}), 404
        return jsonify({'error': 'Could not find similar documents'}), 500

if __name__ == '__main__':
    logger.info("Starting server on http://localhost:5000")
    app.run(debug=False)