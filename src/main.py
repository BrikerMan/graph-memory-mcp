import logging
from contextlib import asynccontextmanager
from textwrap import dedent
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException

from src.schema import (
    CreateEntitiesRequest,
    # Entity-related schema models
    CreateEntityRequest,
    CreateEntityResponse,
    ReadEntityRequest,
    ReadEntityResponse,
    UpdateEntityRequest,
    UpdateEntityResponse,
    # Observation-related schema models
    CreateObservationRequest,
    CreateObservationsRequest,
    CreateObservationsResponse,
    # Relation-related schema models
    CreateRelationRequest,
    CreateRelationsRequest,
    CreateRelationsResponse,
    DeleteEntitiesRequest,
    DeleteEntitiesResponse,
    DeleteObservationsRequest,
    DeleteObservationsResponse,
    DeleteRelationsBySourceTargetRequest,
    DeleteRelationsBySourceTargetResponse,
    DeleteRelationsRequest,
    DeleteRelationsResponse,
    ErrorResponse,
    ListDatabasesResponse,
    ReadGraphRequest,
    ReadGraphResponse,
    # Existing schema models
    Relation,
    # Search and read schema models
    SearchNodesRequest,
    SearchNodesResponse,
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


# Dependency to get storage instance
def get_storage() -> MemoryStorage:
    """Dependency function to get MemoryStorage instance."""
    return MemoryStorage()


# API Endpoints


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "bm-graph-memory-mcp"}


@app.post("/entity", response_model=ReadEntityResponse)
async def read_entity(
    request: ReadEntityRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Read a specific entity from the knowledge graph."""
    try:
        # Extract the entity name
        entity_name = request.name
        
        # Read the entity
        context = request.context if request.context is not None else "main"
        entity = storage.memory_read_entity(entity_name, context)
        
        if not entity:
            return ReadEntityResponse(
                success=False,
                entity=None,
                message=f"Entity '{entity_name}' not found in context '{context}'"
            )
        
        return ReadEntityResponse(
            success=True,
            entity=entity,
            message=f"Entity '{entity_name}' retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error reading entity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Entity endpoints

@app.post("/entities", response_model=CreateEntityResponse)
async def create_entity(
    request: CreateEntityRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create a new entity in the knowledge graph."""
    try:
        # Prepare entity object
        entity = {
            "name": request.name,
            "entity_type": request.entity_type,
            "type": "entity",
        }
        
        # Add optional fields if provided
        if request.attributes:
            # Add all attributes to the entity
            for key, value in request.attributes.items():
                entity[key] = value
        
        # Add initial observations if provided
        if request.initial_observations:
            entity["observations"] = request.initial_observations
        
        # Create the entity
        context = request.context if request.context is not None else "main"
        created_names = storage.memory_create_entities([entity], context)
        
        if not created_names:
            return CreateEntityResponse(
                success=False,
                created_names=[],
                message=f"Failed to create entity with name '{request.name}'. It may already exist."
            )
        
        return CreateEntityResponse(
            success=True,
            created_names=created_names,
            message="Entity created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating entity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/entities/batch", response_model=CreateEntityResponse)
async def create_entities(
    request: CreateEntitiesRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create multiple entities at once in the knowledge graph."""
    try:
        # Create the entities
        context = request.context if request.context is not None else "main"
        created_names = storage.memory_create_entities(request.entities, context)
        
        return CreateEntityResponse(
            success=True,
            created_names=created_names,
            message=f"Created {len(created_names)} entities successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating entities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/entities", response_model=DeleteEntitiesResponse)
async def delete_entities(
    request: DeleteEntitiesRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Delete entities from the knowledge graph."""
    try:
        # Delete the entities
        context = request.context if request.context is not None else "main"
        deleted_names = storage.memory_delete_entities(request.entity_names, context)
        
        return DeleteEntitiesResponse(
            success=True,
            deleted_names=deleted_names,
            message=f"Deleted {len(deleted_names)} entities successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting entities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Relation endpoints

@app.post("/relations", response_model=CreateRelationsResponse)
async def create_relation(
    request: CreateRelationRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create a new relation in the knowledge graph."""
    try:
        # Prepare relation object
        relation = {
            "source": request.source,
            "target": request.target,
            "relation_type": request.relation_type,
            "type": "relation",
            "directed": request.directed if request.directed is not None else True,
        }
        
        # Add optional fields if provided
        if request.attributes:
            # Add all attributes to the relation
            for key, value in request.attributes.items():
                relation[key] = value
        
        # Create the relation
        context = request.context if request.context is not None else "main"
        created_count = storage.memory_create_relations([relation], context)
        
        if created_count == 0:
            return CreateRelationsResponse(
                success=False,
                created_count=0,
                message=f"Failed to create relation between '{request.source}' and '{request.target}'. The entities may not exist."
            )
        
        return CreateRelationsResponse(
            success=True,
            created_count=created_count,
            message="Relation created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating relation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/relations/batch", response_model=CreateRelationsResponse)
async def create_relations(
    request: CreateRelationsRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create multiple relations at once in the knowledge graph."""
    try:
        # Create the relations
        context = request.context if request.context is not None else "main"
        created_count = storage.memory_create_relations(request.relations, context)
        
        return CreateRelationsResponse(
            success=True,
            created_count=created_count,
            message=f"Created {created_count} relations successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating relations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/relations", response_model=DeleteRelationsBySourceTargetResponse)
async def delete_relations(
    request: DeleteRelationsBySourceTargetRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Delete relations from the knowledge graph by source and target entities."""
    try:
        # Delete the relations
        context = request.context if request.context is not None else "main"
        deleted_count = storage.memory_delete_relations(
            request.source, 
            request.target, 
            request.relation_type, 
            context
        )
        
        return DeleteRelationsBySourceTargetResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} relations successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting relations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Observation endpoints

@app.post("/observations", response_model=CreateObservationsResponse)
async def create_observation(
    request: CreateObservationRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create a new observation for an entity in the knowledge graph."""
    try:
        # Extract the entity name and content
        entity_name = request.entity_name
        content = request.content
        
        # Create the observation
        context = request.context if request.context is not None else "main"
        observation_count = storage.memory_add_observations(entity_name, [content], context)
        
        if observation_count == 0:
            return CreateObservationsResponse(
                success=False,
                entity_name=entity_name,
                observation_count=0,
                message=f"Failed to create observation for entity '{entity_name}'. The entity may not exist."
            )
        
        return CreateObservationsResponse(
            success=True,
            entity_name=entity_name,
            observation_count=observation_count,
            message="Observation added successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating observation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/observations/batch", response_model=CreateObservationsResponse)
async def create_observations(
    request: CreateObservationsRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Create multiple observations at once for an entity in the knowledge graph."""
    try:
        # Extract the entity name and observations
        entity_name = request.entity_name
        observations = request.observations
        
        # Create the observations
        context = request.context if request.context is not None else "main"
        observation_count = storage.memory_add_observations(entity_name, observations, context)
        
        return CreateObservationsResponse(
            success=True,
            entity_name=entity_name,
            observation_count=observation_count,
            message=f"Added {observation_count} observations successfully to entity '{entity_name}'"
        )
        
    except Exception as e:
        logger.error(f"Error creating observations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/observations", response_model=DeleteObservationsResponse)
async def delete_observations(
    request: DeleteObservationsRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Delete observations from an entity in the knowledge graph."""
    try:
        # Extract the entity name and observation indices
        entity_name = request.entity_name
        observation_indices = request.observation_indices
        
        # Delete the observations
        context = request.context if request.context is not None else "main"
        deleted_count = storage.memory_delete_observations(entity_name, observation_indices, context)
        
        return DeleteObservationsResponse(
            success=True,
            entity_name=entity_name,
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} observations from entity '{entity_name}' successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting observations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Search and read endpoints

@app.post("/search", response_model=SearchNodesResponse)
async def search_nodes(
    request: SearchNodesRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Search for information in the knowledge graph using keywords."""
    try:
        # Search the graph
        results = storage.memory_search_nodes(request.keywords, request.contexts)
        
        return SearchNodesResponse(
            success=True,
            results=results,
            message=f"Search completed successfully with {sum(len(records) for records in results.values())} total matches"
        )
        
    except Exception as e:
        logger.error(f"Error searching nodes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph", response_model=ReadGraphResponse)
async def read_graph(
    request: ReadGraphRequest,
    storage: MemoryStorage = Depends(get_storage)
):
    """Read the entire graph or specific contexts."""
    try:
        # Read the graph
        data = storage.memory_read_graph(request.contexts)
        
        return ReadGraphResponse(
            success=True,
            data=data,
            message=f"Retrieved data from {len(data)} contexts"
        )
        
    except Exception as e:
        logger.error(f"Error reading graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/databases", response_model=ListDatabasesResponse)
async def list_databases(
    storage: MemoryStorage = Depends(get_storage)
):
    """List all available memory databases (contexts)."""
    try:
        # List the databases
        contexts = storage.memory_list_databases()
        
        return ListDatabasesResponse(
            success=True,
            contexts=contexts,
            message=f"Found {len(contexts)} database contexts"
        )
        
    except Exception as e:
        logger.error(f"Error listing databases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
