import sys
import os
import tempfile
import shutil
import pytest
from pathlib import Path

# Add the src directory to the Python path to allow for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_memory_folder():
    """
    Fixture that creates a temporary directory for memory storage.
    
    This fixture sets up a temporary directory, sets the MEMORY_FOLDER
    environment variable to point to it, and cleans it up after the test.
    
    Returns:
        Path: The path to the temporary directory
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Set the MEMORY_FOLDER environment variable
    original_value = os.environ.get("MEMORY_FOLDER")
    os.environ["MEMORY_FOLDER"] = temp_dir
    
    # Yield the path to the temporary directory
    yield Path(temp_dir)
    
    # Clean up
    if original_value:
        os.environ["MEMORY_FOLDER"] = original_value
    else:
        del os.environ["MEMORY_FOLDER"]
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_entities():
    """
    Fixture that returns a list of sample entity records.
    
    Returns:
        list: A list of entity records
    """
    return [
        {"type": "entity", "name": "Person1", "entityType": "person", "observations": ["Observation about Person1"]},
        {"type": "entity", "name": "Place1", "entityType": "place", "observations": ["Observation about Place1"]},
        {"type": "entity", "name": "Concept1", "entityType": "concept", "observations": ["Observation about Concept1"]},
    ]


@pytest.fixture
def sample_relations():
    """
    Fixture that returns a list of sample relation records.
    
    Returns:
        list: A list of relation records
    """
    return [
        {"type": "relation", "source": "Person1", "target": "Place1", "relationType": "visited", "directed": True},
        {"type": "relation", "source": "Person1", "target": "Concept1", "relationType": "understands", "directed": True},
        {"type": "relation", "source": "Place1", "target": "Concept1", "relationType": "represents", "directed": False},
    ]
