import json
import logging
from contextlib import asynccontextmanager
from textwrap import dedent
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.schema import (
    # Observation operations
    AddObservationsRequestV2,
    # Entity operations
    CreateEntitiesRequestV2,
    # Relation operations
    CreateRelationsRequestV2,
    DeleteEntityRequestV2,
    DeleteObservationsRequestV2,
    DeleteRelationsRequestV2,
    ErrorResponseV2,
    ListDatabasesResponseV2,
    ReadEntitiesRequestV2,
    ReadEntitiesResponseV2,
    ReadRelationsResponseV2,
    # Search and database operations
    SearchNodesRequestV2,
    # Core schema models
    _BaseEntity,
    _BaseRelation,
)
from src.storage import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler for startup and shutdown events."""
    logger.info("Starting Brikerman Graph Memory MCP Server...")

    # Initialize storage directories if needed
    storage = MemoryStorage()
    storage.initialize_storage()

    yield

    logger.info("Shutting down Brikerman Graph Memory MCP Server...")


# Initialize FastAPI app with metadata
app = FastAPI(
    title="Brikerman Graph Memory MCP",
    description=dedent("""
        Brikerman Graph Memory MCP Server - FastAPI Implementation

        A persistent, indexed knowledge graph for AI agents, designed for MCP-compatible platforms.
        This FastAPI server provides REST endpoints for managing a knowledge graph composed of
        entities, relationships, and observations.

        Core Concepts:
        - The 'main' database acts as the core index and routing table
        - Contexts provide specialized memories for specific topics
        """),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get storage instance
def get_storage() -> MemoryStorage:
    """Dependency function to get MemoryStorage instance."""
    return MemoryStorage()


def normalize_context(context: Optional[str]) -> str:
    """
    Normalize the context value, treating 'main', 'default', and empty string as 'main'.
    
    Args:
        context: The context value to normalize
        
    Returns:
        Normalized context string
    """
    if not context or context in ["main", "default", ""]:
        return "main"
    return context


# API Endpoints

# Health check endpoint
@app.get("/health", include_in_schema=False, operation_id="health_check")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "bm-graph-memory-mcp"}


# ===== Core Tools =====

@app.post("/memory_create_entities", response_model=ReadEntitiesResponseV2, operation_id="memory_create_entities")
async def memory_create_entities(
    request: CreateEntitiesRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Add new entities (like people, places, or concepts) to the knowledge graph.
    
    This endpoint creates multiple entities at once in the specified context.
    """
    try:
        # Create the entities
        context = normalize_context(request.context)
        created_names = storage.memory_create_entities([entity.model_dump() for entity in request.entities], context)
        
        # Return the created entities
        entities = []
        for name in created_names:
            entity_data = storage.memory_read_entity(name, context)
            if entity_data:
                entity = _BaseEntity(
                    name=entity_data.get("name"),
                    entity_type=entity_data.get("entity_type") or entity_data.get("entityType"),
                    observations=entity_data.get("observations", [])
                )
                entities.append(entity)
        
        return ReadEntitiesResponseV2(
            success=True,
            data=[{"context": context, "entities": entities}]
        )
        
    except Exception as e:
        logger.error(f"Error creating entities: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="EntityCreationError"
        )


@app.post("/memory_create_relations", response_model=ReadRelationsResponseV2, operation_id="memory_create_relations")
async def memory_create_relations(
    request: CreateRelationsRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Create labeled links between existing entities in the knowledge graph.
    
    This endpoint creates multiple relations at once in the specified context.
    """
    try:
        # Create the relations
        context = normalize_context(request.context)
        storage.memory_create_relations([relation.model_dump() for relation in request.relations], context)
        
        # Get all relations in the context to return
        records = storage.load_database(context)
        relations = []
        
        for record in records:
            if record.get("type") == "relation":
                relation = _BaseRelation(
                    source=record.get("source"),
                    target=record.get("target"),
                    relation_type=record.get("relation_type") or record.get("relationType"),
                    directed=record.get("directed", True)
                )
                relations.append(relation)
        
        return ReadRelationsResponseV2(
            success=True,
            data=[{"context": context, "relations": relations}]
        )
        
    except Exception as e:
        logger.error(f"Error creating relations: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="RelationCreationError"
        )


@app.post("/memory_add_observations", response_model=ReadEntitiesResponseV2, operation_id="memory_add_observations")
async def memory_add_observations(
    request: AddObservationsRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Add new pieces of text information to an existing entity.
    
    This endpoint adds observations to an entity in the specified context.
    """
    try:
        # Add observations to the entity
        context = normalize_context(request.context)
        added_count = storage.memory_add_observations(request.name, request.observations, context)
        
        if added_count == 0:
            return ErrorResponseV2(
                success=False,
                error=f"Entity '{request.name}' not found in context '{context}'",
                error_type="EntityNotFoundError"
            )
        
        # Get the updated entity
        entity_data = storage.memory_read_entity(request.name, context)
        if not entity_data:
            return ErrorResponseV2(
                success=False,
                error=f"Entity '{request.name}' not found after adding observations",
                error_type="EntityRetrievalError"
            )
            
        entity = _BaseEntity(
            name=entity_data.get("name"),
            entity_type=entity_data.get("entity_type") or entity_data.get("entityType"),
            observations=entity_data.get("observations", [])
        )
        
        return ReadEntitiesResponseV2(
            success=True,
            data=[{"context": context, "entities": [entity]}]
        )
        
    except Exception as e:
        logger.error(f"Error adding observations: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="ObservationAdditionError"
        )


@app.post("/memory_search_nodes", response_model=ReadEntitiesResponseV2, operation_id="memory_search_nodes")
async def memory_search_nodes(
    request: SearchNodesRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Search for entities in the knowledge graph using keywords and optional pattern matching (wildcards supported).

    - Supports both keywords and pattern search.
    - Pattern supports wildcards, e.g. '*2025*' (any text containing 2025) or 'diet*' (text starting with 'diet').
    - Results always include the full contents of the 'main' database.
    - For full data dump without search, use /memory_read_graph instead.
    """
    try:
        # Search the graph
        results = storage.memory_search_nodes(request.keywords, request.contexts, request.pattern)
        
        # Convert the results to the response format
        data = []
        total_entities = 0
        
        for context, records in results.items():
            entities = []
            
            for record in records:
                if record.get("type") == "entity":
                    entity = _BaseEntity(
                        name=record.get("name"),
                        entity_type=record.get("entity_type") or record.get("entityType"),
                        observations=record.get("observations", [])
                    )
                    entities.append(entity)
            
            if entities:
                data.append({"context": context, "entities": entities})
                total_entities += len(entities)
        
        # If no matching entities were found, return a list of all entity names to help the agent
        if total_entities == 0:
            # Get all available contexts
            all_contexts = storage.list_contexts()
            all_entity_names = []
            
            # Collect entity names from all contexts
            for ctx in all_contexts:
                try:
                    records = storage.load_database(ctx)
                    for record in records:
                        if record.get("type") == "entity":
                            entity_name = record.get("name")
                            if entity_name and entity_name not in all_entity_names:
                                all_entity_names.append(entity_name)
                except ValueError:
                    # Skip invalid contexts
                    continue
            
            # If we found entity names, create a special response
            if all_entity_names:
                # Create a single entity with a special name and type
                # The observations will contain all available entity names
                entity = _BaseEntity(
                    name="__all_available_entities__",
                    entity_type="__entity_list__",
                    observations=all_entity_names
                )
                data.append({"context": "available_entities", "entities": [entity]})
        
        return ReadEntitiesResponseV2(
            success=True,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error searching nodes: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="SearchError"
        )


@app.post("/memory_read_graph", response_model=ReadEntitiesResponseV2, operation_id="memory_read_graph")
async def memory_read_graph(
    request: ReadEntitiesRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Read all entities from one or more databases (contexts). Does NOT support keyword or pattern search.

    - Only returns complete entity data, does NOT support pattern or search functionality.
    - For keyword or pattern search, use /memory_search_nodes instead.
    """
    # Only reads all entities, does NOT support pattern or any content filtering
    try:
        # Read all entities from all specified contexts without filtering
        graph_data = storage.memory_read_graph(request.contexts if request.contexts else None)
        data = []
        
        for context, records in graph_data.items():
            entities = []
            
            for record in records:
                if record.get("type") == "entity":
                    entity = _BaseEntity(
                        name=record.get("name"),
                        entity_type=record.get("entity_type") or record.get("entityType"),
                        observations=record.get("observations", [])
                    )
                    entities.append(entity)
            
            if entities:
                data.append({"context": context, "entities": entities})
        
        return ReadEntitiesResponseV2(
            success=True,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error reading graph: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="GraphReadError"
        )


# ===== Management & Deletion Tools =====

@app.get("/memory_list_databases", response_model=ListDatabasesResponseV2, operation_id="memory_list_databases")
async def memory_list_databases(
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Show all available memory databases (contexts).
    """
    try:
        # List the databases
        contexts = storage.memory_list_databases()
        
        return ListDatabasesResponseV2(
            success=True,
            contexts=contexts
        )
        
    except Exception as e:
        logger.error(f"Error listing databases: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="DatabaseListingError"
        )


@app.post("/memory_delete_entities", response_model=ReadEntitiesResponseV2, operation_id="memory_delete_entities")
async def memory_delete_entities(
    request: DeleteEntityRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Remove entities from the graph.
    """
    try:
        # Delete the entity
        context = normalize_context(request.context)
        deleted_names = storage.memory_delete_entities([request.name], context)
        
        if not deleted_names:
            return ErrorResponseV2(
                success=False,
                error=f"Entity '{request.name}' not found in context '{context}'",
                error_type="EntityNotFoundError"
            )
        
        # Return empty entities list to indicate successful deletion
        return ReadEntitiesResponseV2(
            success=True,
            data=[{"context": context, "entities": []}]
        )
        
    except Exception as e:
        logger.error(f"Error deleting entity: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="EntityDeletionError"
        )


@app.post("/memory_delete_relations", response_model=ReadRelationsResponseV2, operation_id="memory_delete_relations")
async def memory_delete_relations(
    request: DeleteRelationsRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Remove specific relationships between entities.
    """
    try:
        # Delete the relations
        context = normalize_context(request.context)
        deleted_count = storage.memory_delete_relations(
            request.source, 
            request.target, 
            request.relation_type, 
            context
        )
        
        if deleted_count == 0:
            return ErrorResponseV2(
                success=False,
                error=f"No relations found between '{request.source}' and '{request.target}' in context '{context}'",
                error_type="RelationNotFoundError"
            )
        
        # Get remaining relations
        records = storage.load_database(context)
        remaining_relations = []
        
        for record in records:
            if record.get("type") == "relation" and record.get("source") == request.source and record.get("target") == request.target:
                relation = _BaseRelation(
                    source=record.get("source"),
                    target=record.get("target"),
                    relation_type=record.get("relation_type") or record.get("relationType"),
                    directed=record.get("directed", True)
                )
                remaining_relations.append(relation)
        
        return ReadRelationsResponseV2(
            success=True,
            data=[{"context": context, "relations": remaining_relations}]
        )
        
    except Exception as e:
        logger.error(f"Error deleting relations: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="RelationDeletionError"
        )


@app.post("/memory_delete_observations", response_model=ReadEntitiesResponseV2, operation_id="memory_delete_observations")
async def memory_delete_observations(
    request: DeleteObservationsRequestV2,
    storage: MemoryStorage = Depends(get_storage)
):
    """
    Remove specific observations from an entity.
    """
    try:
        # Get the entity to identify observation indices
        context = normalize_context(request.context)
        entity_data = storage.memory_read_entity(request.name, context)
        
        if not entity_data or "observations" not in entity_data:
            return ErrorResponseV2(
                success=False,
                error=f"Entity '{request.name}' not found or has no observations in context '{context}'",
                error_type="EntityNotFoundError"
            )
        
        # Find indices of observations to delete
        observations = entity_data.get("observations", [])
        indices_to_delete = []
        
        for i, obs in enumerate(observations):
            if obs in request.observations:
                indices_to_delete.append(i)
        
        if not indices_to_delete:
            return ErrorResponseV2(
                success=False,
                error=f"No matching observations found for entity '{request.name}' in context '{context}'",
                error_type="ObservationNotFoundError"
            )
        
        # Delete the observations
        storage.memory_delete_observations(request.name, indices_to_delete, context)
        
        # Get the updated entity
        updated_entity_data = storage.memory_read_entity(request.name, context)
        if not updated_entity_data:
            return ErrorResponseV2(
                success=False,
                error=f"Entity '{request.name}' not found after deleting observations",
                error_type="EntityRetrievalError"
            )
            
        entity = _BaseEntity(
            name=updated_entity_data.get("name"),
            entity_type=updated_entity_data.get("entity_type") or updated_entity_data.get("entityType"),
            observations=updated_entity_data.get("observations", [])
        )
        
        return ReadEntitiesResponseV2(
            success=True,
            data=[{"context": context, "entities": [entity]}]
        )
        
    except Exception as e:
        logger.error(f"Error deleting observations: {str(e)}")
        return ErrorResponseV2(
            success=False,
            error=str(e),
            error_type="ObservationDeletionError"
        )