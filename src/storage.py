"""
Handles file storage operations for the bm-graph-memory system.

Implements safety checks with _bm_gm markers and provides
JSONL file operations for the knowledge graph data.
Storage location is determined by the MEMORY_FOLDER environment variable.
"""

import json
import logging
import os
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Safety marker for bm_gm system
BM_GM_SAFETY_MARKER = {"type": "_bm_gm", "source": "brikerman-graph-memory-mcp"}


class MemoryStorage:
    """
    Handles file storage operations for the bm-graph-memory system.
    
    Implements safety checks with _bm_gm markers and provides
    JSONL file operations for the knowledge graph data.
    Storage location is determined by the MEMORY_FOLDER environment variable.
    """
    
    def __init__(self):
        # Use MEMORY_FOLDER environment variable or default to ~/.bm
        memory_folder = os.environ.get("MEMORY_FOLDER")
        self.storage_path = Path(memory_folder) if memory_folder else Path.home() / ".bm"
    
    def get_storage_path(self) -> Path:
        """
        Get the storage path based on MEMORY_FOLDER environment variable.
            
        Returns:
            Path to the storage directory
        """
        return self.storage_path
    
    def initialize_storage(self):
        """
        Initialize storage directory and create main database if needed.
        """
        storage_path = self.get_storage_path()
        storage_path.mkdir(exist_ok=True)
        
        main_db_path = storage_path / "memory.jsonl"
        if not main_db_path.exists():
            self._create_empty_database(main_db_path)
            logger.info(f"Created main database at {main_db_path}")
    
    def _create_empty_database(self, db_path: Path):
        """Create an empty database file with safety marker."""
        with open(db_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
    
    def _validate_database_file(self, db_path: Path) -> bool:
        """
        Validate that a database file has the proper _bm_gm safety marker.
        
        Args:
            db_path: Path to the database file
            
        Returns:
            True if file is valid, False otherwise
        """
        if not db_path.exists():
            return False
            
        try:
            with open(db_path, 'r') as f:
                first_line = f.readline().strip()
                if not first_line:
                    return False
                
                marker = json.loads(first_line)
                return (marker.get("type") == "_bm_gm" and 
                       marker.get("source") == "brikerman-graph-memory-mcp")
        except (json.JSONDecodeError, IOError):
            return False
    
    def get_database_path(self, context: Optional[str] = "main") -> Path:
        """
        Get the file path for a specific context database.
        
        Args:
            context: Database context name (defaults to 'main')
            
        Returns:
            Path to the database file
        """
        storage_path = self.get_storage_path()
        
        # Treat 'main', 'default', and empty string as the main database
        if not context or context in ["main", "default", ""]:
            return storage_path / "memory.jsonl"
        else:
            return storage_path / f"memory-{context}.jsonl"
    
    def load_database(self, context: Optional[str] = "main") -> List[Dict[str, Any]]:
        """
        Load all records from a database file.
        
        Args:
            context: Database context name
            
        Returns:
            List of database records (excluding safety marker)
        """
        db_path = self.get_database_path(context)
        
        if not self._validate_database_file(db_path):
            raise ValueError(f"Invalid or missing database file: {db_path}")
        
        records = []
        with open(db_path, 'r') as f:
            lines = f.readlines()
            
            # Skip the first line (safety marker)
            for line in lines[1:]:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON line in {db_path}: {line}")
        
        return records
    
    def save_database(self, records: List[Dict[str, Any]], context: Optional[str] = "main"):
        """
        Save records to a database file.
        
        Args:
            records: List of records to save
            context: Database context name
        """
        db_path = self.get_database_path(context)
        
        # Ensure directory exists
        db_path.parent.mkdir(exist_ok=True)
        
        with open(db_path, 'w') as f:
            # Write safety marker first
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
            
            # Write all records
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def list_contexts(self) -> List[str]:
        """
        List all available database contexts.
            
        Returns:
            List of context names
        """
        storage_path = self.get_storage_path()
        
        if not storage_path.exists():
            return []
        
        contexts = []
        
        # Check for main database
        if (storage_path / "memory.jsonl").exists():
            contexts.append("main")
        
        # Check for context-specific databases
        for file_path in storage_path.glob("memory-*.jsonl"):
            context_name = file_path.stem.replace("memory-", "")
            if self._validate_database_file(file_path):
                contexts.append(context_name)
        
        return contexts
        
    def memory_create_entities(self, entities: List[Dict[str, Any]], context: str = "main") -> List[str]:
        """
        Add new entities (people, places, concepts) to the knowledge graph.
        
        Args:
            entities: List of entity objects to add (must include name and entity_type)
            context: Database context name (defaults to 'main')
            
        Returns:
            List of entity names that were created
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        # Load existing database
        try:
            records = self.load_database(context)
        except ValueError:
            # If database doesn't exist, create it
            db_path = self.get_database_path(context)
            self._create_empty_database(db_path)
            records = []
        
        # Extract existing entity names in this context to avoid duplicates
        existing_entities = {
            record.get("name") for record in records 
            if record.get("type") == "entity" and "name" in record
        }
        
        # Track created entity names
        created_names = []
        
        # Process each entity
        for entity in entities:
            # Ensure entity has required fields
            if "name" not in entity or "entity_type" not in entity:
                logger.warning("Skipping entity without required name or entity_type")
                continue
                
            entity_name = entity["name"]
            
            # Skip if entity already exists in this context
            if entity_name in existing_entities:
                logger.warning(f"Entity with name '{entity_name}' already exists in context '{context}', skipping")
                continue
            
            # Add type marker if not present
            if "type" not in entity:
                entity["type"] = "entity"
            
            # Initialize empty observations list if not present
            if "observations" not in entity:
                entity["observations"] = []
                
            # Rename entity_type to entityType to match our schema
            if "entity_type" in entity and "entityType" not in entity:
                entity["entityType"] = entity["entity_type"]
                del entity["entity_type"]
            
            # Add initial observations if provided
            if "initial_observations" in entity and entity["initial_observations"]:
                entity["observations"] = entity["initial_observations"]
                del entity["initial_observations"]
            
            # Add to records and track name
            records.append(entity)
            created_names.append(entity_name)
            existing_entities.add(entity_name)
        
        # Save updated database
        self.save_database(records, context)
        
        return created_names
        
    def memory_create_relations(self, relations: List[Dict[str, Any]], context: str = "main") -> int:
        """
        Create labeled links between existing entities in the knowledge graph.
        
        Args:
            relations: List of relation objects to add (must include source, target, and relation_type)
            context: Database context name (defaults to 'main')
            
        Returns:
            Number of relations that were created
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        # Load existing database
        try:
            records = self.load_database(context)
        except ValueError:
            # If database doesn't exist, create it
            db_path = self.get_database_path(context)
            self._create_empty_database(db_path)
            records = []
        
        # Extract existing entity names for validation
        entity_names = {
            record.get("name") for record in records 
            if record.get("type") == "entity" and "name" in record
        }
        
        # Track created relations count
        created_count = 0
        
        # Process each relation
        for relation in relations:
            # Ensure relation has required fields
            required_fields = ["source", "target", "relation_type"]
            if not all(field in relation for field in required_fields):
                missing = [f for f in required_fields if f not in relation]
                logger.warning(f"Skipping relation missing required fields: {missing}")
                continue
                
            source_name = relation["source"]
            target_name = relation["target"]
            
            # Validate that source and target entities exist
            if source_name not in entity_names:
                logger.warning(f"Source entity '{source_name}' does not exist in context '{context}', skipping relation")
                continue
                
            if target_name not in entity_names:
                logger.warning(f"Target entity '{target_name}' does not exist in context '{context}', skipping relation")
                continue
            
            # Add type marker if not present
            if "type" not in relation:
                relation["type"] = "relation"
            
            # Rename relation_type to relationType to match our schema
            if "relation_type" in relation and "relationType" not in relation:
                relation["relationType"] = relation["relation_type"]
                del relation["relation_type"]
            
            # Add to records and increment count
            records.append(relation)
            created_count += 1
        
        # Save updated database
        self.save_database(records, context)
        
        return created_count
        
    def memory_add_observations(self, entity_name: str, observations: List[str], context: str = "main") -> int:
        """
        Add text information to an existing entity in the knowledge graph.
        
        Args:
            entity_name: Name of the entity to add observations to
            observations: List of observation text contents to add
            context: Database context name (defaults to 'main')
            
        Returns:
            Number of observations that were added
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        # Load existing database
        try:
            records = self.load_database(context)
        except ValueError:
            # If database doesn't exist, create it
            db_path = self.get_database_path(context)
            self._create_empty_database(db_path)
            records = []
        
        # Find the entity to update
        entity_found = False
        observations_added = 0
        
        for record in records:
            if record.get("type") == "entity" and record.get("name") == entity_name:
                entity_found = True
                
                # Ensure the entity has an observations list
                if "observations" not in record:
                    record["observations"] = []
                    
                # Add new observations
                for observation in observations:
                    record["observations"].append(observation)
                    observations_added += 1
                
                break
        
        if not entity_found:
            logger.warning(f"Entity '{entity_name}' not found in context '{context}', no observations added")
            return 0
        
        # Save updated database
        self.save_database(records, context)
        
        return observations_added
        
    def memory_search_nodes(self, keywords: List[str], contexts: Optional[List[str]] = None, pattern: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for information in the knowledge graph using keywords and/or pattern matching.
        
        Args:
            keywords: List of keywords to search for
            contexts: List of context names to search in (if None, search in all contexts)
            pattern: Optional wildcard pattern to match entity names (e.g., "*2025*", "diet*")
            
        Returns:
            Dictionary mapping context names to lists of matching records
            The results will always include the full contents of the 'main' database.
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        # If no contexts specified, search all available contexts
        if contexts is None:
            contexts = self.list_contexts()
        
        # Ensure 'main' is always included
        if "main" not in contexts:
            contexts.append("main")
            
        results = {}
        
        # Process each context
        for context in contexts:
            try:
                records = self.load_database(context)
            except ValueError:
                # Skip invalid databases
                logger.warning(f"Skipping invalid database context: {context}")
                continue
            
            # For 'main' context, include all records regardless of keywords
            if context == "main":
                results[context] = records
                continue
            
            # For other contexts, filter by keywords and pattern
            matching_records = []
            
            for record in records:
                # Check if record should be included based on pattern matching of entity name
                if pattern and record.get("type") == "entity":
                    entity_name = record.get("name", "")
                    if not self._matches_pattern(entity_name, pattern):
                        continue
                
                # Check each field in the record for keyword matches
                if keywords:
                    record_str = json.dumps(record).lower()
                    if not any(keyword.lower() in record_str for keyword in keywords):
                        continue
                
                # If we get here, the record matched all criteria
                matching_records.append(record)
            
            if matching_records:
                results[context] = matching_records
                
        return results
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """
        Check if text matches a wildcard pattern.
        
        Args:
            text: The text to check
            pattern: A wildcard pattern (e.g., "*2025*", "diet*")
            
        Returns:
            True if the text matches the pattern, False otherwise
        """
        # Convert wildcard pattern to regex pattern
        regex_pattern = pattern.replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"
        
        # Match using regex
        return bool(re.match(regex_pattern, text, re.IGNORECASE))
        
    def memory_read_graph(self, contexts: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Dump the entire content of one or more databases.
        
        Args:
            contexts: List of context names to read (if None, read all contexts)
            
        Returns:
            Dictionary mapping context names to lists of records
            The results will always include the full contents of the 'main' database.
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        # If no contexts specified, read all available contexts
        if contexts is None:
            contexts = self.list_contexts()
        
        # Ensure 'main' is always included
        if "main" not in contexts:
            contexts.append("main")
            
        results = {}
        
        # Process each context
        for context in contexts:
            try:
                records = self.load_database(context)
                results[context] = records
            except ValueError:
                # Skip invalid databases
                logger.warning(f"Skipping invalid database context: {context}")
                continue
                
        return results
        
    def memory_list_databases(self) -> List[str]:
        """
        Show all available memory databases (contexts).
        
        Returns:
            List of available context names
        """
        # This is essentially the same as list_contexts
        return self.list_contexts()
        
    def memory_delete_entities(self, entity_names: List[str], context: str = "main") -> List[str]:
        """
        Remove entities from the graph.
        
        Args:
            entity_names: List of entity names to remove
            context: Database context name (defaults to 'main')
            
        Returns:
            List of entity names that were successfully removed
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        try:
            records = self.load_database(context)
        except ValueError:
            logger.warning(f"Invalid or missing database context: {context}")
            return []
        
        deleted_names = []
        updated_records = []
        
        # Create a set for faster lookups
        entity_names_set = set(entity_names)
        
        # Also remove related relations
        for record in records:
            record_type = record.get("type")
            
            if record_type == "entity" and record.get("name") in entity_names_set:
                # Skip this entity (effectively removing it)
                deleted_names.append(record.get("name"))
                continue
                
            elif record_type == "relation" and (record.get("source") in entity_names_set or record.get("target") in entity_names_set):
                # Skip relations that involve deleted entities
                continue
                
            # Keep all other records
            updated_records.append(record)
        
        # Save updated database
        self.save_database(updated_records, context)
        
        return deleted_names
        
    def memory_delete_relations(self, source: str, target: str, relation_type: Optional[str] = None, context: str = "main") -> int:
        """
        Remove specific relationships between entities.
        
        Args:
            source: Name of the source entity
            target: Name of the target entity
            relation_type: Type of relation to delete (if None, deletes all relations between entities)
            context: Database context name (defaults to 'main')
            
        Returns:
            Number of relations that were successfully removed
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        try:
            records = self.load_database(context)
        except ValueError:
            logger.warning(f"Invalid or missing database context: {context}")
            return 0
        
        deleted_count = 0
        updated_records = []
        remaining_relations = []
        
        # Remove specified relations
        for record in records:
            if record.get("type") == "relation" and record.get("source") == source and record.get("target") == target:
                # If relation_type is specified, only delete relations of that type
                if relation_type is None or record.get("relationType") == relation_type:
                    # Skip this relation (effectively removing it)
                    deleted_count += 1
                    continue
                else:
                    # Keep this relation and add to remaining_relations
                    remaining_relations.append(record)
            
            # Keep all other records
            updated_records.append(record)
        
        # Save updated database
        self.save_database(updated_records, context)
        
        return deleted_count
        
    def memory_delete_observations(self, entity_name: str, observation_indices: List[int], context: str = "main") -> int:
        """
        Remove specific observations from an entity.
        
        Args:
            entity_name: Name of the entity to remove observations from
            observation_indices: List of observation indices (0-based) to remove
            context: Database context name (defaults to 'main')
            
        Returns:
            Number of observations that were successfully removed
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        try:
            records = self.load_database(context)
        except ValueError:
            logger.warning(f"Invalid or missing database context: {context}")
            return 0
        
        deleted_count = 0
        entity_found = False
        
        # Sort indices in descending order to avoid shifting issues
        observation_indices = sorted(observation_indices, reverse=True)
        
        # Find the entity and remove observations
        for record in records:
            if record.get("type") == "entity" and record.get("name") == entity_name:
                entity_found = True
                
                if "observations" not in record or not record["observations"]:
                    logger.warning(f"Entity '{entity_name}' has no observations to delete")
                    break
                
                # Delete observations at the specified indices
                for index in observation_indices:
                    if 0 <= index < len(record["observations"]):
                        del record["observations"][index]
                        deleted_count += 1
                    else:
                        logger.warning(f"Invalid observation index {index} for entity '{entity_name}'")
                
                break
        
        if not entity_found:
            logger.warning(f"Entity '{entity_name}' not found in context '{context}', no observations deleted")
            return 0
        
        # Save updated database
        self.save_database(records, context)
        
        return deleted_count
        
        
    def memory_read_entity(self, entity_name: str, context: Optional[str] = "main") -> Optional[Dict[str, Any]]:
        """
        Read a specific entity from the knowledge graph.
        
        Args:
            entity_name: Name of the entity to read
            context: Database context name (defaults to 'main')
            
        Returns:
            The entity data if found, None otherwise
        """
        # Initialize storage if needed
        self.initialize_storage()
        
        try:
            records = self.load_database(context)
        except ValueError:
            logger.warning(f"Invalid or missing database context: {context}")
            return None
        
        # Find the entity with the given name
        for record in records:
            if record.get("type") == "entity" and record.get("name") == entity_name:
                return record
                
        # Entity not found
        return None
