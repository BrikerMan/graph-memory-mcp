import pytest
from fastapi.testclient import TestClient

from src.main import app

@pytest.fixture
def client():
    """
    Fixture that returns a test client for the FastAPI app.
    
    Returns:
        TestClient: A test client for the FastAPI app
    """
    return TestClient(app)


def test_search_returns_all_entities_when_empty(client, temp_memory_folder):
    """
    Test that searching with non-matching keywords returns a list of all available entities.
    """
    # First create some test entities
    entities_request = {
        "entities": [
            {"name": "TestEntity1", "entity_type": "test", "observations": ["Observation 1"]},
            {"name": "TestEntity2", "entity_type": "test", "observations": ["Observation 2"]}
        ],
        "context": "main"
    }
    client.post("/memory_create_entities", json=entities_request)
    
    # Search with keywords that don't match any entity
    request_data = {
        "keywords": ["xyz123_definitely_not_found_anywhere"],
        "contexts": ["main"]
    }
    
    # Send the request
    response = client.post("/memory_search_nodes", json=request_data)
    
    # The API should return success=True
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    
    # Print the actual response for debugging
    print(f"Response data: {response_data}")
    
    # Check that we get a special entity with all entity names
    found_entity_list = False
    all_entity_names = []
    
    for context_data in response_data["data"]:
        for entity in context_data["entities"]:
            if entity["name"] == "__all_available_entities__" and entity["entity_type"] == "__entity_list__":
                found_entity_list = True
                all_entity_names = entity["observations"]
                break
    
    # Assert that we found the special entity
    assert found_entity_list, "Special entity list not found in response"
    
    # Assert that all test entities are in the list
    assert "TestEntity1" in all_entity_names
    assert "TestEntity2" in all_entity_names