import os
import pytest
from unittest.mock import patch
from src.storage import MemoryStorage

@pytest.fixture
def setup_memory():
    """Set up a temporary memory folder for testing."""
    test_folder = "test_memory"
    os.makedirs(test_folder, exist_ok=True)
    with patch.dict(os.environ, {"MEMORY_FOLDER": test_folder}):
        storage = MemoryStorage()
        storage.initialize_storage()
        
        # Create entities in 'main' context
        storage.memory_create_entities([
            {"name": "critical-info-001", "entity_type": "info"},
            {"name": "critical-info-002", "entity_type": "info"}
        ], "main")

        # Create entities in 'work' context
        storage.memory_create_entities([
            {"name": "work-2025-09-01", "entity_type": "meeting"},
            {"name": "work-2025-09-02", "entity_type": "meeting"},
            {"name": "project-alpha-report", "entity_type": "report"}
        ], "work")

        # Create entities in 'personal' context
        storage.memory_create_entities([
            {"name": "diet-log-2025-09-20", "entity_type": "log"},
            {"name": "diet-plan-2025", "entity_type": "plan"}
        ], "personal")
        
        yield storage
        
        # Teardown: clean up the created memory files
        for file_name in os.listdir(test_folder):
            os.remove(os.path.join(test_folder, file_name))
        os.rmdir(test_folder)

def test_search_main_always_returns_full_content(setup_memory: MemoryStorage):
    """The 'main' context should always be fully returned, regardless of keywords."""
    results = setup_memory.memory_search_nodes(keywords=["nonexistent"])
    
    main_records = results.get("main", [])
    main_entities = {record["name"] for record in main_records if record.get("type") == "entity"}
    
    assert "critical-info-001" in main_entities
    assert "critical-info-002" in main_entities
    assert len(main_entities) == 2

def test_search_in_specific_context_with_pattern(setup_memory: MemoryStorage):
    """Search in a specific context ('work') with a wildcard pattern."""
    results = setup_memory.memory_search_nodes(keywords=[], contexts=["work"], pattern="work-2025-09-*")
    
    work_records = results.get("work", [])
    work_entities = {record["name"] for record in work_records if record.get("type") == "entity"}
    assert "work-2025-09-01" in work_entities
    assert "work-2025-09-02" in work_entities
    assert "project-alpha-report" not in work_entities
    
    main_records = results.get("main", [])
    main_entities = {record["name"] for record in main_records if record.get("type") == "entity"}
    assert "critical-info-001" in main_entities
    assert "critical-info-002" in main_entities

def test_search_with_keyword_and_pattern(setup_memory: MemoryStorage):
    """Search across all contexts with a keyword and a pattern."""
    results = setup_memory.memory_search_nodes(keywords=["diet"], pattern="*2025*")
    
    personal_records = results.get("personal", [])
    personal_entities = {record["name"] for record in personal_records if record.get("type") == "entity"}
    assert "diet-log-2025-09-20" in personal_entities
    assert "diet-plan-2025" in personal_entities
    
    main_records = results.get("main", [])
    main_entities = {record["name"] for record in main_records if record.get("type") == "entity"}
    assert "critical-info-001" in main_entities
    assert "critical-info-002" in main_entities

def test_search_with_broad_pattern_across_contexts(setup_memory: MemoryStorage):
    """Search with a broad pattern that matches entities in multiple contexts."""
    results = setup_memory.memory_search_nodes(keywords=[], pattern="*2025*")
    
    work_records = results.get("work", [])
    work_entities = {record["name"] for record in work_records if record.get("type") == "entity"}
    assert "work-2025-09-01" in work_entities
    assert "work-2025-09-02" in work_entities
    
    personal_records = results.get("personal", [])
    personal_entities = {record["name"] for record in personal_records if record.get("type") == "entity"}
    assert "diet-log-2025-09-20" in personal_entities
    assert "diet-plan-2025" in personal_entities
    
    main_records = results.get("main", [])
    main_entities = {record["name"] for record in main_records if record.get("type") == "entity"}
    assert "critical-info-001" in main_entities
    assert "critical-info-002" in main_entities

def test_search_no_results_except_main(setup_memory: MemoryStorage):
    """Search with a pattern that matches no entities; should still return 'main'."""
    results = setup_memory.memory_search_nodes(keywords=[], pattern="nonexistent-pattern-*")
    
    # No entities from other contexts should be returned
    other_entities = {
        record["name"]
        for context, records in results.items()
        if context != "main"
        for record in records
        if record.get("type") == "entity"
    }
    assert not other_entities
    
    main_records = results.get("main", [])
    main_entities = {record["name"] for record in main_records if record.get("type") == "entity"}
    assert "critical-info-001" in main_entities
    assert "critical-info-002" in main_entities
    assert len(main_entities) == 2