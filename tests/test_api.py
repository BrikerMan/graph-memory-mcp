import json
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.storage import MemoryStorage, BM_GM_SAFETY_MARKER


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    """
    return TestClient(app)


@pytest.fixture
def initialized_memory_folder(temp_memory_folder):
    """
    Set up a memory folder with initialized databases and sample data.
    
    Returns:
        Path: The path to the temporary directory with initialized databases
    """
    # Initialize the storage with safety markers
    storage = MemoryStorage()
    storage.initialize_storage()
    
    # Create the main database with safety marker
    main_db_path = temp_memory_folder / "memory.jsonl"
    with open(main_db_path, "w") as f:
        f.write(json.dumps(BM_GM_SAFETY_MARKER) + "\n")
    
    # Create a test context database
    test_db_path = temp_memory_folder / "memory-test.jsonl"
    with open(test_db_path, "w") as f:
        f.write(json.dumps(BM_GM_SAFETY_MARKER) + "\n")
    
    return temp_memory_folder


# Test the health check endpoint
def test_health_check(client):
    """
    Test the health check endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "bm-graph-memory-mcp"}


# Tests for the Core Tools

def test_memory_create_entities(client, initialized_memory_folder):
    """
    Test creating entities in the knowledge graph.
    """
    # Prepare the request
    request_data = {
        "entities": [
            {"name": "Alice", "entity_type": "person", "observations": ["CEO of Tech Corp"]},
            {"name": "TechCorp", "entity_type": "organization", "observations": ["A technology company"]}
        ],
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_create_entities", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert len(response_data["data"]) == 1
    assert response_data["data"][0]["context"] == "main"
    assert len(response_data["data"][0]["entities"]) == 2
    
    # Verify entity names in response
    entity_names = [entity["name"] for entity in response_data["data"][0]["entities"]]
    assert "Alice" in entity_names
    assert "TechCorp" in entity_names


def test_memory_create_relations(client, initialized_memory_folder):
    """
    Test creating relations between entities in the knowledge graph.
    """
    # First create some entities
    entities_request = {
        "entities": [
            {"name": "Bob", "entity_type": "person", "observations": ["CTO of Tech Corp"]},
            {"name": "DataCorp", "entity_type": "organization", "observations": ["A data company"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Now create relations between them
    request_data = {
        "relations": [
            {"source": "Bob", "target": "DataCorp", "relation_type": "works_at", "directed": True}
        ],
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_create_relations", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert len(response_data["data"]) == 1
    assert response_data["data"][0]["context"] == "main"
    
    # There might be multiple relations in the context now
    found_relation = False
    for relation in response_data["data"][0]["relations"]:
        if (relation["source"] == "Bob" and 
            relation["target"] == "DataCorp" and 
            relation["relation_type"] == "works_at"):
            found_relation = True
            break
    
    assert found_relation, "Created relation not found in response"


def test_memory_add_observations(client, initialized_memory_folder):
    """
    Test adding observations to an existing entity.
    """
    # First create an entity
    entities_request = {
        "entities": [
            {"name": "Charlie", "entity_type": "person", "observations": ["Initial observation"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Now add observations to it
    request_data = {
        "name": "Charlie",
        "observations": ["New observation 1", "New observation 2"],
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_add_observations", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert len(response_data["data"]) == 1
    assert response_data["data"][0]["context"] == "main"
    assert len(response_data["data"][0]["entities"]) == 1
    
    # Verify the entity has all observations
    entity = response_data["data"][0]["entities"][0]
    assert entity["name"] == "Charlie"
    assert len(entity["observations"]) == 3  # Initial + 2 new
    assert "Initial observation" in entity["observations"]
    assert "New observation 1" in entity["observations"]
    assert "New observation 2" in entity["observations"]


def test_memory_search_nodes(client, initialized_memory_folder):
    """
    Test searching for nodes in the knowledge graph.
    """
    # First create some entities with specific keywords
    entities_request = {
        "entities": [
            {"name": "David", "entity_type": "person", "observations": ["Expert in machine learning"]},
            {"name": "AI Project", "entity_type": "project", "observations": ["A project about artificial intelligence"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Search for nodes with keyword "machine"
    request_data = {
        "keywords": ["machine"],
        "contexts": ["main"]
    }
    
    # Send the request
    response = client.post("/memory_search_nodes", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Check that the entity with "machine" was found
    found_entity = False
    for context_data in response_data["data"]:
        for entity in context_data["entities"]:
            if entity["name"] == "David" and "Expert in machine learning" in entity["observations"]:
                found_entity = True
                break
    
    assert found_entity, "Entity with matching keyword not found in search results"


def test_memory_read_graph(client, initialized_memory_folder):
    """
    Test reading the entire graph or specific contexts.
    """
    # First create some entities in both main and test contexts
    main_entities_request = {
        "entities": [
            {"name": "Eve", "entity_type": "person", "observations": ["Main context entity"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=main_entities_request)
    
    test_entities_request = {
        "entities": [
            {"name": "Frank", "entity_type": "person", "observations": ["Test context entity"]}
        ],
        "context": "test"
    }
    client.post("/memory_create_entities", json=test_entities_request)
    
    # Read the entire graph
    request_data = {
        "contexts": ["main", "test"]
    }
    
    # Send the request
    response = client.post("/memory_read_graph", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Check that entities from both contexts are included
    main_entity_found = False
    test_entity_found = False
    
    for context_data in response_data["data"]:
        context = context_data["context"]
        for entity in context_data["entities"]:
            if context == "main" and entity["name"] == "Eve":
                main_entity_found = True
            elif context == "test" and entity["name"] == "Frank":
                test_entity_found = True
    
    assert main_entity_found, "Entity in main context not found"
    assert test_entity_found, "Entity in test context not found"


# Tests for Management & Deletion Tools

def test_memory_list_databases(client, initialized_memory_folder):
    """
    Test listing all available memory databases (contexts).
    """
    # First create entities in a new context to ensure it exists
    entities_request = {
        "entities": [
            {"name": "Grace", "entity_type": "person", "observations": ["Entity in new context"]}
        ],
        "context": "new_context"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # List all databases
    response = client.get("/memory_list_databases")
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Check that both contexts are in the list
    assert "main" in response_data["contexts"]
    assert "new_context" in response_data["contexts"]
    assert "test" in response_data["contexts"]


def test_memory_delete_entities(client, initialized_memory_folder):
    """
    Test removing entities from the graph.
    """
    # First create an entity to delete
    entities_request = {
        "entities": [
            {"name": "Henry", "entity_type": "person", "observations": ["Entity to be deleted"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Now delete the entity
    request_data = {
        "name": "Henry",
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_delete_entities", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Verify the entity is deleted by trying to read the graph
    read_request = {
        "contexts": ["main"]
    }
    read_response = client.post("/memory_read_graph", json=read_request)
    read_data = read_response.json()
    
    # Check that the deleted entity is not in the graph
    deleted_entity_found = False
    for context_data in read_data["data"]:
        if context_data["context"] == "main":
            for entity in context_data["entities"]:
                if entity["name"] == "Henry":
                    deleted_entity_found = True
                    break
    
    assert not deleted_entity_found, "Deleted entity was still found in the graph"


def test_memory_delete_relations(client, initialized_memory_folder):
    """
    Test removing specific relationships between entities.
    """
    # First create entities and a relation to delete
    entities_request = {
        "entities": [
            {"name": "Ivy", "entity_type": "person", "observations": ["Person entity"]},
            {"name": "Project X", "entity_type": "project", "observations": ["Project entity"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    relations_request = {
        "relations": [
            {"source": "Ivy", "target": "Project X", "relation_type": "manages", "directed": True}
        ],
        "context": "main"
    }
    client.post("/memory_create_relations", json=relations_request)
    
    # Now delete the relation
    request_data = {
        "source": "Ivy",
        "target": "Project X",
        "relation_type": "manages",
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_delete_relations", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Check that the relation is no longer present
    deleted_relation_found = False
    for context_data in response_data["data"]:
        if context_data["context"] == "main":
            for relation in context_data["relations"]:
                if (relation["source"] == "Ivy" and 
                    relation["target"] == "Project X" and 
                    relation["relation_type"] == "manages"):
                    deleted_relation_found = True
                    break
    
    assert not deleted_relation_found, "Deleted relation was still found in the response"


def test_memory_delete_observations(client, initialized_memory_folder):
    """
    Test removing specific observations from an entity.
    """
    # First create an entity with multiple observations
    entities_request = {
        "entities": [
            {"name": "Jack", "entity_type": "person", "observations": [
                "Observation to keep", 
                "Observation to delete",
                "Another observation to keep"
            ]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Now delete one of the observations
    request_data = {
        "name": "Jack",
        "observations": ["Observation to delete"],
        "context": "main"
    }
    
    # Send the request
    response = client.post("/memory_delete_observations", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert len(response_data["data"]) == 1
    assert response_data["data"][0]["context"] == "main"
    assert len(response_data["data"][0]["entities"]) == 1
    
    # Verify the observation was deleted
    entity = response_data["data"][0]["entities"][0]
    assert entity["name"] == "Jack"
    assert len(entity["observations"]) == 2
    assert "Observation to keep" in entity["observations"]
    assert "Another observation to keep" in entity["observations"]
    assert "Observation to delete" not in entity["observations"]


# Error case tests

def test_entity_not_found_error(client, initialized_memory_folder):
    """
    Test error handling when an entity is not found.
    """
    # Try to add observations to a non-existent entity
    request_data = {
        "name": "NonExistentEntity",
        "observations": ["This should fail"],
        "context": "main"
    }
    
    # Try to add observations to a non-existent entity
    # We'll catch the ResponseValidationError and check its content
    try:
        client.post("/memory_add_observations", json=request_data)
        assert False, "Expected ResponseValidationError was not raised"
    except Exception as e:
        # Check that the error message contains the expected text
        error_text = str(e)
        assert "EntityNotFoundError" in error_text
        assert "NonExistentEntity" in error_text


def test_delete_nonexistent_relation(client, initialized_memory_folder):
    """
    Test error handling when trying to delete a non-existent relation.
    """
    # Try to delete a relation that doesn't exist
    request_data = {
        "source": "SourceEntity",
        "target": "TargetEntity",
        "relation_type": "nonexistent_relation",
        "context": "main"
    }
    
    # Try to delete a relation that doesn't exist
    # We'll catch the ResponseValidationError and check its content
    try:
        client.post("/memory_delete_relations", json=request_data)
        assert False, "Expected ResponseValidationError was not raised"
    except Exception as e:
        # Check that the error message contains the expected text
        error_text = str(e)
        assert "RelationNotFoundError" in error_text
        assert "No relations found between" in error_text


def test_creating_duplicate_entity(client, initialized_memory_folder):
    """
    Test creating an entity that already exists.
    """
    # First create an entity
    entities_request = {
        "entities": [
            {"name": "DuplicateEntity", "entity_type": "test", "observations": ["First instance"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Try to create the same entity again
    response = client.post("/memory_create_entities", json=entities_request)
    
    # The API should still return success but update the entity
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Now check that the entity exists with the original observation
    read_request = {
        "contexts": ["main"]
    }
    read_response = client.post("/memory_read_graph", json=read_request)
    read_data = read_response.json()
    
    # Find the entity and check its observations
    entity_found = False
    for context_data in read_data["data"]:
        if context_data["context"] == "main":
            for entity in context_data["entities"]:
                if entity["name"] == "DuplicateEntity":
                    entity_found = True
                    assert "First instance" in entity["observations"]
                    break
    
    assert entity_found, "Entity not found after duplicate creation attempt"


def test_search_with_nonexistent_context(client, initialized_memory_folder):
    """
    Test searching in a context that doesn't exist.
    """
    # First create an entity in the main context to ensure it exists
    entities_request = {
        "entities": [
            {"name": "SearchTestEntity", "entity_type": "test", "observations": ["Entity for search test"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Search for nodes in a non-existent context
    request_data = {
        "keywords": ["test"],
        "contexts": ["nonexistent_context"]
    }
    
    # Send the request
    response = client.post("/memory_search_nodes", json=request_data)
    
    # The API should return success=True
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # In our implementation, only valid contexts are included in the results
    # So no results from nonexistent_context should be returned
    contexts_in_results = [data["context"] for data in response_data["data"]]
    assert "nonexistent_context" not in contexts_in_results