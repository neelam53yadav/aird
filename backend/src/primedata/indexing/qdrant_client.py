"""
Qdrant client for vector storage and retrieval.

This module provides functionality to interact with Qdrant vector database
for storing and retrieving embeddings.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)

class QdrantClient:
    """Client for interacting with Qdrant vector database."""
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, grpc_port: Optional[int] = None):
        """
        Initialize Qdrant client.
        
        Args:
            host: Qdrant host (defaults to environment variable or localhost)
            port: Qdrant HTTP port (defaults to environment variable or 6333)
            grpc_port: Qdrant gRPC port (defaults to environment variable or 6334)
        """
        self.host = host or os.getenv('QDRANT_HOST', 'localhost')
        self.port = port or int(os.getenv('QDRANT_PORT', '6333'))
        self.grpc_port = grpc_port or int(os.getenv('QDRANT_GRPC_PORT', '6334'))
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Qdrant client."""
        try:
            from qdrant_client import QdrantClient as QdrantClientLib
            from qdrant_client.http import models
            
            self.client = QdrantClientLib(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=False  # Use HTTP by default
            )
            
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            logger.info(f"Found {len(collections.collections)} existing collections")
            
        except ImportError:
            logger.error("qdrant-client not installed. Install with: pip install qdrant-client")
            self.client = None
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant at {self.host}:{self.port}: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if client is connected to Qdrant."""
        return self.client is not None
    
    def ensure_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> bool:
        """
        Ensure a collection exists with the specified configuration.
        
        Args:
            collection_name: Name of the collection
            vector_size: Size of the vectors
            distance: Distance metric (Cosine, Dot, Euclid)
            
        Returns:
            True if collection exists or was created successfully
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return False
        
        try:
            from qdrant_client.http import models
            
            # Check if collection exists
            try:
                collection_info = self.client.get_collection(collection_name)
                logger.info(f"Collection {collection_name} already exists")
                return True
            except Exception:
                # Collection doesn't exist, create it
                pass
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=getattr(models.Distance, distance.upper())
                )
            )
            
            logger.info(f"Created collection {collection_name} with vector size {vector_size}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure collection {collection_name}: {e}")
            return False
    
    def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        """
        Upsert points to a collection.
        
        Args:
            collection_name: Name of the collection
            points: List of points to upsert, each containing 'id', 'vector', and 'payload'
            
        Returns:
            True if upsert was successful
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return False
        
        if not points:
            logger.warning("No points to upsert")
            return True
        
        try:
            from qdrant_client.http import models
            
            # Convert points to Qdrant format
            qdrant_points = []
            for point in points:
                qdrant_points.append(
                    models.PointStruct(
                        id=point['id'],
                        vector=point['vector'],
                        payload=point['payload']
                    )
                )
            
            # Upsert points
            self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points
            )
            
            logger.info(f"Upserted {len(points)} points to collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert points to collection {collection_name}: {e}")
            return False
    
    def search_points(self, collection_name: str, query_vector: List[float], limit: int = 10, 
                     score_threshold: Optional[float] = None, filter_conditions: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar points in a collection.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector for similarity search
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            filter_conditions: Optional filter conditions
            
        Returns:
            List of search results
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return []
        
        try:
            from qdrant_client.http import models
            
            # Build search request
            search_request = models.SearchRequest(
                vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vector=False
            )
            
            if score_threshold is not None:
                search_request.score_threshold = score_threshold
            
            if filter_conditions is not None:
                search_request.filter = self._build_filter(filter_conditions)
            
            # Perform search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_request.filter if filter_conditions else None
            )
            
            # Convert results to list of dicts
            search_results = []
            for result in results:
                search_results.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                })
            
            logger.info(f"Found {len(search_results)} results for search in collection {collection_name}")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search points in collection {collection_name}: {e}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection information or None if not found
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return None
        
        try:
            collection_info = self.client.get_collection(collection_name)
            
            return {
                'name': collection_name,
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'points_count': collection_info.points_count,
                'segments_count': collection_info.segments_count,
                'config': {
                    'vector_size': collection_info.config.params.vectors.size,
                    'distance': collection_info.config.params.vectors.distance
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_name}: {e}")
            return None
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if deletion was successful
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return False
        
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        if not self.is_connected():
            logger.error("Qdrant client not connected")
            return []
        
        try:
            collections = self.client.get_collections()
            return [collection.name for collection in collections.collections]
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def _build_filter(self, filter_conditions: Dict) -> Any:
        """
        Build Qdrant filter from conditions.
        
        Args:
            filter_conditions: Filter conditions dictionary
            
        Returns:
            Qdrant filter object
        """
        try:
            from qdrant_client.http import models
            
            # Simple filter building - can be extended for more complex conditions
            conditions = []
            
            for key, value in filter_conditions.items():
                if isinstance(value, list):
                    # Must match any of the values
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value)
                        )
                    )
                else:
                    # Must match exact value
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
            
            if len(conditions) == 1:
                return conditions[0]
            else:
                return models.Filter(must=conditions)
                
        except Exception as e:
            logger.error(f"Failed to build filter: {e}")
            return None

    def set_prod_alias(self, workspace_id: str, product_id: str, version: int) -> bool:
        """
        Set production alias to point to a specific version collection.
        
        Args:
            workspace_id: Workspace ID
            product_id: Product ID
            version: Version number to promote
            
        Returns:
            True if alias was set successfully, False otherwise
        """
        try:
            from qdrant_client.http import models
            
            # Create alias name and collection name
            alias_name = f"prod_ws_{workspace_id}__prod_{product_id}"
            collection_name = f"ws_{workspace_id}__prod_{product_id}__v_{version}"
            
            # Check if the target collection exists
            collections = self.client.get_collections()
            collection_exists = any(col.name == collection_name for col in collections.collections)
            
            if not collection_exists:
                logger.error(f"Collection {collection_name} does not exist")
                return False
            
            # Create or update the alias using direct HTTP API
            import requests
            
            # First, try to delete existing alias if it exists
            try:
                existing_aliases = self.client.get_aliases()
                for alias in existing_aliases.aliases:
                    if alias.alias_name == alias_name:
                        # Delete existing alias
                        delete_payload = {
                            "actions": [
                                {"delete_alias": {"alias_name": alias_name}}
                            ]
                        }
                        response = requests.post(
                            f"http://{self.host}:{self.port}/collections/aliases",
                            json=delete_payload,
                            headers={"Content-Type": "application/json"}
                        )
                        if response.status_code == 200:
                            logger.info(f"Deleted existing alias '{alias_name}'")
                        break
            except Exception as e:
                logger.warning(f"Could not check/delete existing aliases: {e}")
            
            # Create the new alias
            create_payload = {
                "actions": [
                    {"create_alias": {"collection_name": collection_name, "alias_name": alias_name}}
                ]
            }
            
            response = requests.post(
                f"http://{self.host}:{self.port}/collections/aliases",
                json=create_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Created production alias '{alias_name}' -> '{collection_name}'")
            else:
                raise Exception(f"Failed to create alias: {response.status_code} - {response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set production alias: {e}")
            return False

    def get_prod_alias_collection(self, workspace_id: str, product_id: str) -> Optional[str]:
        """
        Get the collection name that the production alias points to.
        
        Args:
            workspace_id: Workspace ID
            product_id: Product ID
            
        Returns:
            Collection name if alias exists, None otherwise
        """
        try:
            alias_name = f"prod_ws_{workspace_id}__prod_{product_id}"
            
            # Get all aliases using direct HTTP API
            import requests
            response = requests.get(f"http://{self.host}:{self.port}/aliases")
            
            if response.status_code == 200:
                data = response.json()
                for alias in data.get('result', {}).get('aliases', []):
                    if alias.get('alias_name') == alias_name:
                        return alias.get('collection_name')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get production alias: {e}")
            return None


# Global Qdrant client instance
qdrant_client = QdrantClient()
