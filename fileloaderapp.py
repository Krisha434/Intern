import os
import sqlite3
import logging
import shutil
import json
from flask import Flask, request, jsonify
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from sentence_transformers import SentenceTransformer
from search_strategies.loader import FileLoader, LoaderError
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
logger.info("Starting File Loader Document Management System")

# Configuration
UPLOAD_FOLDER = 'documents'
INDEX_DIR = 'index'
DB_PATH = 'filedata.db'
ALLOWED_EXTENSIONS = {'pdf', 'md', 'svg', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'txt', 'html'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# Initialize sentence transformer for vector embeddings
logger.info("Loading sentence transformer model")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Failed to load sentence transformer model: {str(e)}")
    raise

# Whoosh schema
schema = Schema(
    doc_id=ID(stored=True, unique=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True),
    category=TEXT(stored=True)
)

def initialize_whoosh_index():
    """Initialize or recover Whoosh search index."""
    try:
        if os.path.exists(INDEX_DIR) and not os.listdir(INDEX_DIR):
            logger.warning("Empty index directory. Creating new Whoosh index.")
            return create_in(INDEX_DIR, schema)
        else:
            logger.info("Opening existing Whoosh index")
            return open_dir(INDEX_DIR)
    except Exception as e:
        logger.error(f"Failed to open Whoosh index: {str(e)}. Creating new one.")
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
        os.makedirs(INDEX_DIR)
        return create_in(INDEX_DIR, schema)

ix = initialize_whoosh_index()

def init_db():
    """Set up SQLite database with documents and file_types tables."""
    logger.info("Setting up database")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Create documents table
        c.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                filename TEXT NOT NULL,
                vector TEXT NOT NULL
            )
        ''')
        # Create file_types table
        c.execute('''
            CREATE TABLE IF NOT EXISTS file_types (
                doc_id INTEGER,
                file_type TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Failed to set up database: {str(e)}")
        raise

init_db()

# Initialize file loader
file_loader = FileLoader()

# Persistent database connection for search strategies
conn = sqlite3.connect(DB_PATH)

# Search strategy classes
class SearchError(Exception):
    """Custom exception for content-based search errors."""
    pass

class SimilarityError(Exception):
    """Custom exception for similarity search errors."""
    pass

class ContentSearchStrategy:
    """Search documents by content using Whoosh index."""
    def __init__(self, ix):
        self.ix = ix

    def search(self, query_str, category=''):
        try:
            with self.ix.searcher() as searcher:
                query_parser = QueryParser('content', self.ix.schema)
                query = query_parser.parse(query_str)
                if category:
                    category_parser = QueryParser('category', self.ix.schema)
                    query = query & category_parser.parse(category)
                results = searcher.search(query, limit=20)
                return [{
                    'id': hit['doc_id'],
                    'title': hit['title'],
                    'category': hit['category']
                } for hit in results]
        except Exception as e:
            logger.error(f"[ContentSearchStrategy] Error with query='{query_str}' category='{category}': {str(e)}")
            raise SearchError(f"Search error: {str(e)}")

class SimilaritySearchStrategy:
    """Find similar documents using vector embeddings."""
    def __init__(self, conn):
        self.conn = conn

    def find_similar(self, doc_id):
        try:
            c = self.conn.cursor()
            c.execute('SELECT vector FROM documents WHERE id = ?', (doc_id,))
            result = c.fetchone()
            if not result:
                raise SimilarityError(f"Document with ID {doc_id} not found.")

            target_vector = np.array(json.loads(result[0]))
            c.execute('SELECT id, title, category, vector FROM documents WHERE id != ?', (doc_id,))
            docs = c.fetchall()

            similarities = []
            for doc in docs:
                doc_vector = np.array(json.loads(doc[3]))
                norm_target = np.linalg.norm(target_vector)
                norm_doc = np.linalg.norm(doc_vector)
                if norm_target == 0 or norm_doc == 0:
                    continue
                similarity = np.dot(target_vector, doc_vector) / (norm_target * norm_doc)
                similarities.append({
                    'id': doc[0],
                    'title': doc[1],
                    'category': doc[2],
                    'similarity': float(similarity)
                })

            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:5]
        except SimilarityError:
            raise
        except Exception as e:
            logger.error(f"[SimilaritySearchStrategy] Error finding similar to doc_id={doc_id}: {str(e)}")
            raise SimilarityError(f"Similarity search error: {str(e)}")

# Initialize search strategies
content_search = ContentSearchStrategy(ix)
similarity_search = SimilaritySearchStrategy(conn)

# Helper functions
def check_file_size(file):
    """Check if file size exceeds limit."""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size {file_size} bytes exceeds limit of {MAX_FILE_SIZE} bytes")
    return file_size

def allowed_file(file):
    """Check if file has allowed extension and size."""
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
        return False
    try:
        check_file_size(file)
        return True
    except ValueError as e:
        logger.warning(f"File size check failed for {file.filename}: {str(e)}")
        return False

def get_vector(text):
    """Generate a 384-dimensional numerical vector embedding for the given text."""
    try:
        embedding = model.encode(text)
        vector = embedding.tolist()
        logger.info(f"Generated vector for text (first 5 elements): {vector[:5]}")
        return vector
    except Exception as e:
        logger.error(f"Failed to generate vector for text: {str(e)}")
        raise

def get_file_type(extension):
    """Determine the file type based on the extension."""
    extension = extension.lower()
    if extension in ['png', 'jpg', 'jpeg']:
        return "Image"
    elif extension == 'pdf':
        return "PDF"
    elif extension == 'md':
        return "Markdown"
    elif extension == 'svg':
        return "SVG"
    elif extension in ['doc', 'docx']:
        return "Word"
    elif extension == 'txt':
        return "Text"
    elif extension == 'html':
        return "HTML"
    else:
        return "Unknown"

# API Endpoints
@app.route('/uploads', methods=['POST'])
def upload_document():
    """Upload a new document, save it, and index it for search."""
    logger.info("Uploading new document")
    if 'file' not in request.files or 'title' not in request.form or 'category' not in request.form:
        logger.warning("Missing required fields in upload request")
        return jsonify({'error': 'Please provide file, title, and category'}), 400

    file = request.files['file']
    title = request.form['title']
    category = request.form['category']

    if not allowed_file(file):
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
            logger.warning(f"Unsupported file type: {file.filename}")
            return jsonify({'error': f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
        return jsonify({'error': f"File size exceeds {MAX_FILE_SIZE} bytes"}), 413

    extension = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{title}_{os.urandom(8).hex()}.{extension}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        file.save(file_path)
    except Exception as e:
        logger.error(f"Failed to save file {filename}: {str(e)}")
        return jsonify({'error': 'Could not save file'}), 500

    try:
        content = file_loader.load(file_path, extension)
    except LoaderError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path}")
        logger.error(f"Failed to process {file_path}: {str(e)}")
        return jsonify({'error': 'Could not process file content'}), 500

    try:
        vector = get_vector(content)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path}")
        return jsonify({'error': 'Could not generate document embedding'}), 500

    try:
        vector_json = json.dumps(vector)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Insert into documents table
        c.execute('INSERT INTO documents (title, category, filename, vector) VALUES (?, ?, ?, ?)',
                  (title, category, filename, vector_json))
        doc_id = c.lastrowid
        # Determine file type and insert into file_types table
        file_type = get_file_type(extension)
        c.execute('INSERT INTO file_types (doc_id, file_type) VALUES (?, ?)',
                  (doc_id, file_type))
        conn.commit()
        conn.close()
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file {file_path}")
        logger.error(f"Database error while saving document {title}: {str(e)}")
        return jsonify({'error': 'Could not save document metadata'}), 500

    try:
        writer = ix.writer()
        writer.add_document(doc_id=str(doc_id), title=title, content=content, category=category)
        writer.commit()
    except Exception as e:
        logger.error(f"Failed to index document {doc_id}: {str(e)}")
        return jsonify({'error': 'Could not index document'}), 500

    logger.info(f"Document uploaded: ID {doc_id}, Title: {title}, File Type: {file_type}")
    return jsonify({'message': 'Document uploaded successfully', 'id': doc_id, 'vector': vector}), 201

@app.route('/uploads/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """Retrieve metadata for a specific document by ID."""
    logger.info(f"Fetching document ID {doc_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, title, category, filename, vector FROM documents WHERE id = ?', (doc_id,))
        doc = c.fetchone()
        # Get the file type from the file_types table
        c.execute('SELECT file_type FROM file_types WHERE doc_id = ?', (doc_id,))
        file_type = c.fetchone()
        conn.close()

        if not doc:
            logger.warning(f"Document ID {doc_id} not found")
            return jsonify({'error': 'Document not found'}), 404

        vector = json.loads(doc[4])
        logger.info(f"Retrieved document ID {doc_id}, Title: {doc[1]}")
        return jsonify({
            'id': doc[0],
            'title': doc[1],
            'category': doc[2],
            'filename': doc[3],
            'vector': vector,
            'file_type': file_type[0] if file_type else 'Unknown'
        }), 200
    except Exception as e:
        logger.error(f"Error fetching document ID {doc_id}: {str(e)}")
        return jsonify({'error': 'Could not fetch document'}), 500

@app.route('/uploads', methods=['GET'])
def list_documents():
    """List metadata for all documents in the database."""
    logger.info("Listing all documents")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Join documents and file_types tables to get file types
        c.execute('''
            SELECT d.id, d.title, d.category, d.filename, d.vector, f.file_type
            FROM documents d
            LEFT JOIN file_types f ON d.id = f.doc_id
        ''')
        docs = c.fetchall()
        conn.close()

        doc_list = [{
            'id': doc[0],
            'title': doc[1],
            'category': doc[2],
            'filename': doc[3],
            'vector': json.loads(doc[4]),
            'file_type': doc[5] if doc[5] else 'Unknown'
        } for doc in docs]
        logger.info(f"Retrieved {len(doc_list)} documents")
        return jsonify(doc_list), 200
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': 'Could not list documents'}), 500

@app.route('/uploads/search', methods=['GET'])
def search_documents():
    """Search documents by content and optionally filter by category."""
    query_str = request.args.get('q', '')
    category = request.args.get('category', '')
    logger.info(f"Searching with query: '{query_str}', category: '{category}'")

    try:
        results = content_search.search(query_str, category)
        logger.info(f"Found {len(results)} results for query '{query_str}'")
        return jsonify(results), 200
    except SearchError as e:
        logger.error(str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/similar/<int:doc_id>', methods=['GET'])
def find_similar_documents(doc_id):
    """Find the top 5 documents similar to the specified document by vector similarity."""
    logger.info(f"Finding similar documents for ID {doc_id}")
    try:
        results = similarity_search.find_similar(doc_id)
        logger.info(f"Found {len(results)} similar documents for ID {doc_id}")
        return jsonify(results), 200
    except SimilarityError as e:
        logger.error(str(e))
        if "not found" in str(e).lower():
            return jsonify({'error': str(e)}), 404
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<int:doc_id>', methods=['DELETE'])
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
        logger.error(f"Error deleting document ID {doc_id}: {str(e)}")
        return jsonify({'error': 'Could not delete document'}), 500

if __name__ == '__main__':
    logger.info("Starting server on http://localhost:5000")
    app.run(debug=False)