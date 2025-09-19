from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any


class Entity(BaseModel):
    type: Literal["entity"] = Field(default="entity", description="Record type identifier")
    name: str = Field(..., description="Unique identifier for the entity within a context")
    entityType: str = Field(..., description="Type/category of the entity")
    observations: List[str] = Field(default_factory=list, description="List of observations about the entity")


class Relation(BaseModel):
    type: Literal["relation"] = Field(default="relation", description="Record type identifier")
    source: str = Field(..., description="Name of the source entity")
    target: str = Field(..., description="Name of the target entity")
    relationType: str = Field(..., description="Type of relationship")
    directed: bool = Field(default=True, description="Whether the relation is directed")


class DeleteRelationsRequest(BaseModel):
    """Request model for deleting relations from the knowledge graph."""
    
    source: str = Field(
        description="Name of the source entity in the relation"
    )
    target: str = Field(
        description="Name of the target entity in the relation"
    )
    relation_type: Optional[str] = Field(
        default=None,
        description="Specific type of relation to delete (if None, deletes all relations between entities)"
    )
    context: Optional[str] = Field(
        default=None,
        description="Database context to target (defaults to 'main')"
    )


class DeleteRelationsResponse(BaseModel):
    """Response model for the delete relations operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    deleted_count: int = Field(description="Number of relations deleted")
    message: str = Field(description="Human-readable status message")
    remaining_relations: List[Relation] = Field(
        default_factory=list,
        description="Remaining relations between the specified entities"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    detail: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")


# New schema models for entity operations

class CreateEntityRequest(BaseModel):
    """Request model for creating a new entity."""
    
    name: str = Field(..., description="Unique identifier for the entity within a context")
    entity_type: str = Field(..., description="Type/category of the entity")
    initial_observations: Optional[List[str]] = Field(default=None, description="Initial observations about the entity")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional attributes for the entity")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateEntitiesRequest(BaseModel):
    """Request model for creating multiple entities at once."""
    
    entities: List[Dict[str, Any]] = Field(..., description="List of entity objects to create (must include name and entity_type)")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateEntityResponse(BaseModel):
    """Response model for the create entity operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    created_names: List[str] = Field(description="Names of entities that were created")
    message: str = Field(description="Human-readable status message")


class DeleteEntitiesRequest(BaseModel):
    """Request model for deleting entities from the knowledge graph."""
    
    entity_names: List[str] = Field(..., description="List of entity names to delete")
    context: Optional[str] = Field(default="main", description="Database context to use")


class DeleteEntitiesResponse(BaseModel):
    """Response model for the delete entities operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    deleted_names: List[str] = Field(description="Names of entities that were deleted")
    message: str = Field(description="Human-readable status message")


# New schema models for relation operations

class CreateRelationRequest(BaseModel):
    """Request model for creating a new relation."""
    
    source: str = Field(..., description="Name of the source entity")
    target: str = Field(..., description="Name of the target entity")
    relation_type: str = Field(..., description="Type of relationship")
    directed: Optional[bool] = Field(default=True, description="Whether the relation is directed")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional attributes for the relation")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateRelationsRequest(BaseModel):
    """Request model for creating multiple relations at once."""
    
    relations: List[Dict[str, Any]] = Field(..., description="List of relation objects to create (must include source, target, and relation_type)")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateRelationsResponse(BaseModel):
    """Response model for the create relations operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    created_count: int = Field(description="Number of relations that were created")
    message: str = Field(description="Human-readable status message")


class DeleteRelationsBySourceTargetRequest(BaseModel):
    """Request model for deleting relations by their source and target entities."""
    
    source: str = Field(..., description="Name of the source entity")
    target: str = Field(..., description="Name of the target entity")
    relation_type: Optional[str] = Field(default=None, description="Specific type of relation to delete (if None, deletes all relations between entities)")
    context: Optional[str] = Field(default="main", description="Database context to use")


class DeleteRelationsBySourceTargetResponse(BaseModel):
    """Response model for the delete relations by source and target operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    deleted_count: int = Field(description="Number of relations that were deleted")
    message: str = Field(description="Human-readable status message")


# New schema models for observation operations

class CreateObservationRequest(BaseModel):
    """Request model for creating a new observation."""
    
    entity_name: str = Field(..., description="Name of the entity this observation is about")
    content: str = Field(..., description="Text content of the observation")
    timestamp: Optional[str] = Field(default=None, description="Timestamp for the observation (ISO format)")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional attributes for the observation")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateObservationsRequest(BaseModel):
    """Request model for creating multiple observations at once."""
    
    entity_name: str = Field(..., description="Name of the entity these observations are about")
    observations: List[str] = Field(..., description="List of observation text contents to add")
    context: Optional[str] = Field(default="main", description="Database context to use")


class CreateObservationsResponse(BaseModel):
    """Response model for the create observations operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    entity_name: str = Field(description="Name of the entity the observations were added to")
    observation_count: int = Field(description="Number of observations that were added")
    message: str = Field(description="Human-readable status message")


class DeleteObservationsRequest(BaseModel):
    """Request model for deleting observations from an entity."""
    
    entity_name: str = Field(..., description="Name of the entity to delete observations from")
    observation_indices: List[int] = Field(..., description="Indices of observations to delete (0-based)")
    context: Optional[str] = Field(default="main", description="Database context to use")


class DeleteObservationsResponse(BaseModel):
    """Response model for the delete observations operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    entity_name: str = Field(description="Name of the entity the observations were deleted from")
    deleted_count: int = Field(description="Number of observations that were deleted")
    message: str = Field(description="Human-readable status message")


# New schema models for search and read operations

class SearchNodesRequest(BaseModel):
    """Request model for searching nodes in the knowledge graph."""
    
    keywords: List[str] = Field(..., description="List of keywords to search for")
    contexts: Optional[List[str]] = Field(default=None, description="List of database contexts to search in")


class SearchNodesResponse(BaseModel):
    """Response model for the search nodes operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    results: Dict[str, List[Dict[str, Any]]] = Field(description="Dictionary mapping context names to lists of matching records")
    message: str = Field(description="Human-readable status message")


class ReadGraphRequest(BaseModel):
    """Request model for reading the entire graph."""
    
    contexts: Optional[List[str]] = Field(default=None, description="List of database contexts to read from")


class ReadGraphResponse(BaseModel):
    """Response model for the read graph operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    data: Dict[str, List[Dict[str, Any]]] = Field(description="Dictionary mapping context names to lists of records")
    message: str = Field(description="Human-readable status message")


class ListDatabasesResponse(BaseModel):
    """Response model for the list databases operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    contexts: List[str] = Field(description="List of available database contexts")
    message: str = Field(description="Human-readable status message")


class UpdateEntityRequest(BaseModel):
    """Request model for updating an existing entity."""
    
    name: str = Field(..., description="Unique identifier for the entity within a context")
    entity_type: Optional[str] = Field(default=None, description="Updated type/category of the entity")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional attributes for the entity")
    context: Optional[str] = Field(default="main", description="Database context to use")


class ReadEntityRequest(BaseModel):
    """Request model for reading a specific entity."""
    
    name: str = Field(..., description="Name of the entity to read")
    context: Optional[str] = Field(default="main", description="Database context to use")


class ReadEntityResponse(BaseModel):
    """Response model for the read entity operation."""
    
    success: bool = Field(description="Whether the operation was successful")
    entity: Optional[Dict[str, Any]] = Field(default=None, description="The requested entity data if found")
    message: str = Field(description="Human-readable status message")