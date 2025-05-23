import numpy as np
import json
from whoosh.qparser import QueryParser
import logging

logger = logging.getLogger(__name__)

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
                    'similarity': similarity
                })

            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:5]
        except SimilarityError:
            raise
        except Exception as e:
            logger.error(f"[SimilaritySearchStrategy] Error finding similar to doc_id={doc_id}: {str(e)}")
            raise SimilarityError(f"Similarity search error: {str(e)}")