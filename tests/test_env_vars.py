import os
import pytest
from pathlib import Path
from storage import MemoryStorage


def test_memory_folder_env_var(temp_memory_folder):
    """Test that MemoryStorage respects the MEMORY_FOLDER environment variable."""
    # The temp_memory_folder fixture sets up the environment variable
    storage = MemoryStorage()
    
    # Check that the storage path matches the temporary directory
    assert storage.get_storage_path() == temp_memory_folder


def test_memory_folder_env_var_change():
    """Test that MemoryStorage responds to changes in the MEMORY_FOLDER environment variable."""
    # Set an initial value
    initial_path = "/tmp/initial_path"
    os.environ["MEMORY_FOLDER"] = initial_path
    storage1 = MemoryStorage()
    
    # Check that the storage path is the initial value
    assert storage1.get_storage_path() == Path(initial_path)
    
    # Change the environment variable
    new_path = "/tmp/new_path"
    os.environ["MEMORY_FOLDER"] = new_path
    
    # Create a new storage instance
    storage2 = MemoryStorage()
    
    # Check that the new instance uses the new path
    assert storage2.get_storage_path() == Path(new_path)
    
    # The original instance should still use the original path
    # (since it stored the path at instantiation)
    assert storage1.get_storage_path() == Path(initial_path)
    
    # Clean up
    del os.environ["MEMORY_FOLDER"]


def test_database_operations_with_fixtures(temp_memory_folder, sample_entities, sample_relations):
    """Test database operations using the provided fixtures."""
    # Create a storage instance
    storage = MemoryStorage()
    storage.initialize_storage()
    
    # Combine entities and relations
    records = sample_entities + sample_relations
    
    # Save the records
    storage.save_database(records)
    
    # Load the records
    loaded_records = storage.load_database()
    
    # Check that all records were loaded correctly
    assert len(loaded_records) == len(records)
    
    # Check that entities were loaded correctly
    loaded_entities = [r for r in loaded_records if r.get("type") == "entity"]
    assert len(loaded_entities) == len(sample_entities)
    
    # Check that relations were loaded correctly
    loaded_relations = [r for r in loaded_records if r.get("type") == "relation"]
    assert len(loaded_relations) == len(sample_relations)
    
    # Check specific entity properties
    person = next(r for r in loaded_entities if r.get("name") == "Person1")
    assert person["entityType"] == "person"
    assert len(person["observations"]) == 1
    
    # Check specific relation properties
    visit_relation = next(r for r in loaded_relations if r.get("relationType") == "visited")
    assert visit_relation["source"] == "Person1"
    assert visit_relation["target"] == "Place1"
    assert visit_relation["directed"] is True