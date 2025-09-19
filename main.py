import json
import logging
from pathlib import Path
from textwrap import dedent
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from schema import Entity, Relation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safety marker for bm_gm system
BM_GM_SAFETY_MARKER = {"type": "_bm_gm", "source": "brikerman-graph-memory-mcp"}


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
        - Storage location is determined by the MEMORY_FOLDER environment variable
        - Safety system using _bm_gm markers and naming conventions
        """),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


class MemoryStorage:
    """
    Handles file storage operations for the bm-graph-memory system.

    Manages both project-local (.bm/) and global storage locations,
    implements safety checks with _bm_gm markers, and provides
    JSONL file operations for the knowledge graph data.
    """

    def __init__(self):
        self.project_path = Path.cwd() / ".bm"
        self.global_path = Path.home() / ".bm"

    def get_storage_path(self, location: Optional[str] = None) -> Path:
        """
        Determine storage path based on location preference and availability.

        Args:
            location: Force 'project' or 'global' storage, or None for auto-detect

        Returns:
            Path to the storage directory
        """
        if location == "project":
            return self.project_path
        elif location == "global":
            return self.global_path
        else:
            # Auto-detect: prefer project-local if .bm directory exists
            return self.project_path if self.project_path.exists() else self.global_path

    def initialize_storage(self, location: Optional[str] = None):
        """
        Initialize storage directory and create main database if needed.

        Args:
            location: Storage location preference
        """
        storage_path = self.get_storage_path(location)
        storage_path.mkdir(exist_ok=True)

        main_db_path = storage_path / "memory.jsonl"
        if not main_db_path.exists():
            self._create_empty_database(main_db_path)
            logger.info(f"Created main database at {main_db_path}")

    def _create_empty_database(self, db_path: Path):
        """Create an empty database file with safety marker."""
        with open(db_path, "w") as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + "\n")

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
            with open(db_path, "r") as f:
                first_line = f.readline().strip()
                if not first_line:
                    return False

                marker = json.loads(first_line)
                return (
                    marker.get("type") == "_bm_gm"
                    and marker.get("source") == "brikerman-graph-memory-mcp"
                )
        except (json.JSONDecodeError, IOError):
            return False

    def get_database_path(
        self, context: str = "main", location: Optional[str] = None
    ) -> Path:
        """
        Get the file path for a specific context database.

        Args:
            context: Database context name (defaults to 'main')
            location: Storage location preference

        Returns:
            Path to the database file
        """
        storage_path = self.get_storage_path(location)

        if context == "main":
            return storage_path / "memory.jsonl"
        else:
            return storage_path / f"memory-{context}.jsonl"

    def load_database(
        self, context: str = "main", location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load all records from a database file.

        Args:
            context: Database context name
            location: Storage location preference

        Returns:
            List of database records (excluding safety marker)
        """
        db_path = self.get_database_path(context, location)

        if not self._validate_database_file(db_path):
            raise ValueError(f"Invalid or missing database file: {db_path}")

        records = []
        with open(db_path, "r") as f:
            lines = f.readlines()

            # Skip the first line (safety marker)
            for line in lines[1:]:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Skipping invalid JSON line in {db_path}: {line}"
                        )

        return records

    def save_database(
        self,
        records: List[Dict[str, Any]],
        context: str = "main",
        location: Optional[str] = None,
    ):
        """
        Save records to a database file.

        Args:
            records: List of records to save
            context: Database context name
            location: Storage location preference
        """
        db_path = self.get_database_path(context, location)

        # Ensure directory exists
        db_path.parent.mkdir(exist_ok=True)

        with open(db_path, "w") as f:
            # Write safety marker first
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + "\n")

            # Write all records
            for record in records:
                f.write(json.dumps(record) + "\n")

    def list_contexts(self, location: Optional[str] = None) -> List[str]:
        """
        List all available database contexts.

        Args:
            location: Storage location preference

        Returns:
            List of context names
        """
        storage_path = self.get_storage_path(location)

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


# Dependency to get storage instance
def get_storage() -> MemoryStorage:
    """Dependency function to get MemoryStorage instance."""
    return MemoryStorage()


# Request/Response Models for API endpoints


class DeleteRelationsRequest(BaseModel):
    """Request model for deleting relations from the knowledge graph."""

    source: str = Field(description="Name of the source entity in the relation")
    target: str = Field(description="Name of the target entity in the relation")
    relation_type: Optional[str] = Field(
        default=None,
        description="Specific type of relation to delete (if None, deletes all relations between entities)",
    )
    context: Optional[str] = Field(
        default=None, description="Database context to target (defaults to 'main')"
    )
    location: Optional[str] = Field(
        default=None, description="Force 'project' or 'global' storage location"
    )


class DeleteRelationsResponse(BaseModel):
    """Response model for the delete relations operation."""

    success: bool = Field(description="Whether the operation was successful")
    deleted_count: int = Field(description="Number of relations deleted")
    message: str = Field(description="Human-readable status message")
    remaining_relations: List[Relation] = Field(
        default_factory=list,
        description="Remaining relations between the specified entities",
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(description="Error message")
    error_type: str = Field(description="Type of error")


# API Endpoints


@app.delete(
    "/memory/relations",
    response_model=DeleteRelationsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Entity or relation not found"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Relations Between Entities",
    description="""
    Removes specific relationships between entities in the knowledge graph.
    
    This endpoint allows you to:
    - Delete all relations between two entities
    - Delete only relations of a specific type between two entities
    - Target specific database contexts (work, personal, etc.)
    - Use either project-local or global storage
    
    **Important Notes:**
    - The 'main' database contents are always included in search results for context
    - Both source and target entities must exist in the specified context
    - If relation_type is not specified, all relations between the entities will be deleted
    - The operation is atomic - either all specified relations are deleted or none
    """,
)
async def delete_relations(
    request: DeleteRelationsRequest, storage: MemoryStorage = Depends(get_storage)
):
    """
    Delete relations between entities in the knowledge graph.

    This endpoint implements the `memory_delete_relations` functionality described
    in the README. It removes specific relationships between entities while maintaining
    the integrity of the knowledge graph.

    Args:
        request: Delete relations request containing source, target, and optional filters
        storage: Memory storage instance (injected dependency)

    Returns:
        DeleteRelationsResponse with operation results

    Raises:
        HTTPException: For various error conditions (404, 400, 500)
    """
    try:
        # Use 'main' context if none specified
        context = request.context or "main"

        # Load the target database
        try:
            records = storage.load_database(context, request.location)
        except ValueError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Database context '{context}' not found or invalid: {str(e)}",
            )

        # Find entities to verify they exist
        entities = {
            record["name"]: record
            for record in records
            if record.get("type") == "entity"
        }

        if request.source not in entities:
            raise HTTPException(
                status_code=404,
                detail=f"Source entity '{request.source}' not found in context '{context}'",
            )

        if request.target not in entities:
            raise HTTPException(
                status_code=404,
                detail=f"Target entity '{request.target}' not found in context '{context}'",
            )

        # Find and filter relations to delete
        relations_to_keep = []
        relations_to_delete = []
        deleted_count = 0

        for record in records:
            if record.get("type") == "relation":
                # Check if this relation matches our deletion criteria
                matches_entities = (
                    (
                        record.get("source") == request.source
                        and record.get("target") == request.target
                    )
                    or
                    # Also check reverse direction for undirected relations
                    (
                        not record.get("directed", True)
                        and record.get("source") == request.target
                        and record.get("target") == request.source
                    )
                )

                if matches_entities:
                    # If relation_type is specified, only delete relations of that type
                    if (
                        request.relation_type is None
                        or record.get("relationType") == request.relation_type
                    ):
                        relations_to_delete.append(record)
                        deleted_count += 1
                    else:
                        relations_to_keep.append(record)
                else:
                    relations_to_keep.append(record)
            else:
                # Keep all non-relation records (entities, observations, etc.)
                relations_to_keep.append(record)

        # Check if any relations were found to delete
        if deleted_count == 0:
            if request.relation_type:
                detail = f"No relations of type '{request.relation_type}' found between '{request.source}' and '{request.target}'"
            else:
                detail = f"No relations found between '{request.source}' and '{request.target}'"

            raise HTTPException(status_code=404, detail=detail)

        # Save the updated database
        storage.save_database(relations_to_keep, context, request.location)

        # Get remaining relations between these entities for response
        remaining_relations = []
        for record in relations_to_keep:
            if record.get("type") == "relation":
                matches_entities = (
                    record.get("source") == request.source
                    and record.get("target") == request.target
                ) or (
                    not record.get("directed", True)
                    and record.get("source") == request.target
                    and record.get("target") == request.source
                )
                if matches_entities:
                    remaining_relations.append(
                        Relation(
                            source=record["source"],
                            target=record["target"],
                            relationType=record["relationType"],
                            directed=record.get("directed", True),
                        )
                    )

        # Prepare success response
        if request.relation_type:
            message = f"Deleted {deleted_count} '{request.relation_type}' relation(s) between '{request.source}' and '{request.target}'"
        else:
            message = f"Deleted {deleted_count} relation(s) between '{request.source}' and '{request.target}'"

        if context != "main":
            message += f" in context '{context}'"

        return DeleteRelationsResponse(
            success=True,
            deleted_count=deleted_count,
            message=message,
            remaining_relations=remaining_relations,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"Unexpected error in delete_relations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "bm-graph-memory-mcp"}
