import os
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Fixture to set up and tear down the test environment."""
    # Set the memory folder for tests
    os.environ["MEMORY_FOLDER"] = "tests/data"
    
    # Ensure the data directory is clean before each test
    data_dir = "tests/data"
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            os.remove(os.path.join(data_dir, f))
    else:
        os.makedirs(data_dir)
        
    yield
    
    # Clean up after tests
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            os.remove(os.path.join(data_dir, f))

def test_create_entities():
    """Test creating entities in the main and a custom context."""
    # Create in main context
    response = client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [
            {"name": "Entity1", "entity_type": "test"},
            {"name": "Entity2", "entity_type": "test"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) == 2
    assert data["data"][0]["entities"][0]["name"] == "Entity1"

    # Create in a new context
    response = client.post("/memory_create_entities", json={
        "context": "work",
        "entities": [
            {"name": "WorkEntity1", "entity_type": "work_test"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) == 1
    assert data["data"][0]["entities"][0]["name"] == "WorkEntity1"

def test_create_relations():
    """Test creating relations between entities."""
    # First, create some entities
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [
            {"name": "EntityA", "entity_type": "test"},
            {"name": "EntityB", "entity_type": "test"}
        ]
    })

    # Create a relation
    response = client.post("/memory_create_relations", json={
        "context": "main",
        "relations": [
            {"source": "EntityA", "target": "EntityB", "relation_type": "connects_to"}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["relations"]) == 1
    assert data["data"][0]["relations"][0]["source"] == "EntityA"
    assert data["data"][0]["relations"][0]["target"] == "EntityB"

def test_add_observations():
    """Test adding observations to an entity."""
    # Create an entity first
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [{"name": "ObservableEntity", "entity_type": "test"}]
    })

    # Add an observation
    response = client.post("/memory_add_observations", json={
        "context": "main",
        "name": "ObservableEntity",
        "observations": ["First observation."]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"][0]["observations"]) == 1
    assert data["data"][0]["entities"][0]["observations"][0] == "First observation."

def test_search_nodes_by_keywords():
    """Test searching for nodes by keywords."""
    # Setup entities
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [
            {"name": "Searchable1", "entity_type": "test", "observations": ["This has a keyword"]},
            {"name": "Searchable2", "entity_type": "test"}
        ]
    })
    client.post("/memory_create_entities", json={
        "context": "work",
        "entities": [
            {"name": "WorkSearch", "entity_type": "test", "observations": ["Work keyword"]}
        ]
    })

    # Search in main
    response = client.post("/memory_search_by_keywords", json={
        "contexts": ["main"],
        "keywords": ["keyword"]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) >= 1
    assert any(e["name"] == "Searchable1" for e in data["data"][0]["entities"])

    # Search in work
    response = client.post("/memory_search_by_keywords", json={
        "contexts": ["work"],
        "keywords": ["Work"]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) >= 1
    assert any(e["name"] == "WorkSearch" for e in data["data"][0]["entities"])

def test_search_nodes_by_pattern():
    """Test searching for nodes by pattern."""
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [
            {"name": "Pattern-A-1", "entity_type": "test"},
            {"name": "Pattern-B-2", "entity_type": "test"}
        ]
    })

    # Search with pattern
    response = client.post("/memory_search_by_pattern", json={
        "contexts": ["main"],
        "patterns": ["Pattern-A-*"]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) >= 1
    assert any(e["name"] == "Pattern-A-1" for e in data["data"][0]["entities"])

def test_read_entities():
    """Test reading all entities from a database."""
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [{"name": "E1", "entity_type": "test"}, {"name": "E2", "entity_type": "test"}]
    })
    client.post("/memory_create_entities", json={
        "context": "work",
        "entities": [{"name": "WE1", "entity_type": "test"}]
    })

    # Read from main
    response = client.post("/memory_read_graph", json={"contexts": ["main"]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"][0]["entities"]) >= 2
    assert {"name": "E1", "entity_type": "test", "observations": []} in data["data"][0]["entities"]
    assert {"name": "E2", "entity_type": "test", "observations": []} in data["data"][0]["entities"]


    # Read from work and main
    response = client.post("/memory_read_graph", json={"contexts": ["work", "main"]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 2 
    
    all_entities = []
    for item in data["data"]:
        all_entities.extend(item["entities"])
    
    assert {"name": "WE1", "entity_type": "test", "observations": []} in all_entities
    assert {"name": "E1", "entity_type": "test", "observations": []} in all_entities
    assert {"name": "E2", "entity_type": "test", "observations": []} in all_entities


def test_list_databases():
    """Test listing all available databases."""
    client.post("/memory_create_entities", json={"context": "db1", "entities": []})
    client.post("/memory_create_entities", json={"context": "db2", "entities": []})

    response = client.get("/memory_list_databases")
    assert response.status_code == 200
    data = response.json()
    assert "main" in data["contexts"]
    assert "db1" in data["contexts"]
    assert "db2" in data["contexts"]

def test_delete_entities():
    """Test deleting entities."""
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [{"name": "ToDelete", "entity_type": "test"}]
    })

    response = client.post("/memory_delete_entities", json={
        "context": "main",
        "name": "ToDelete"
    })
    assert response.status_code == 200
    
    # Verify deletion
    read_response = client.post("/memory_read_graph", json={"contexts": ["main"]})
    read_data = read_response.json()
    
    # Check if data is empty or if the context is not present or if entities are empty
    if not read_data.get("data") or not read_data["data"][0].get("entities"):
        assert True  # Deletion successful, no entities returned
    else:
        assert not any(e["name"] == "ToDelete" for e in read_data["data"][0]["entities"])

def test_delete_relations():
    """Test deleting relations."""
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [{"name": "Src", "entity_type": "test"}, {"name": "Tgt", "entity_type": "test"}]
    })
    client.post("/memory_create_relations", json={
        "context": "main",
        "relations": [{"source": "Src", "target": "Tgt", "relation_type": "rel"}]
    })

    response = client.post("/memory_delete_relations", json={
        "context": "main",
        "source": "Src", 
        "target": "Tgt", 
        "relation_type": "rel"
    })
    assert response.status_code == 200

    # Verify deletion
    read_response = client.post("/memory_read_graph", json={"contexts": ["main"]})
    read_data = read_response.json()
    # Assuming read_graph also returns relations, which it does not based on schema.
    # To verify, we should read relations, but there is no such endpoint.
    # We can assume deletion is successful if status is 200.
    # The current implementation of delete returns remaining relations, let's check that.
    data = response.json()
    assert not data["data"][0]["relations"]


def test_delete_observations():
    """Test deleting observations."""
    client.post("/memory_create_entities", json={
        "context": "main",
        "entities": [{"name": "ObsEnt", "entity_type": "test"}]
    })
    client.post("/memory_add_observations", json={
        "context": "main",
        "name": "ObsEnt",
        "observations": ["obs to delete"]
    })

    response = client.post("/memory_delete_observations", json={
        "context": "main",
        "name": "ObsEnt",
        "observations": ["obs to delete"]
    })
    assert response.status_code == 200

    # Verify deletion
    read_resp_after = client.post("/memory_read_graph", json={"contexts": ["main"]})
    entity_data = read_resp_after.json()["data"][0]["entities"]
    assert not entity_data[0]["observations"]
