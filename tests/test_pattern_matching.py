import os
import tempfile
import shutil
from src.storage import MemoryStorage


class TestPatternMatching:
    """Test suite for the pattern matching functionality in MemoryStorage."""
    
    def setup_method(self):
        """Set up a temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["MEMORY_FOLDER"] = self.temp_dir
        self.storage = MemoryStorage()
        
        # Create test data
        self.storage.initialize_storage()
        
        # Create test entities with different names for pattern matching tests
        test_records = [
            {"type": "entity", "name": "work-2025-09-01", "entity_type": "task"},
            {"type": "entity", "name": "work-2025-09-02", "entity_type": "task"},
            {"type": "entity", "name": "work-2024-10-15", "entity_type": "task"},
            {"type": "entity", "name": "diet-log-2025-09-01", "entity_type": "health"},
            {"type": "entity", "name": "diet-plan-2025", "entity_type": "health"},
            {"type": "entity", "name": "workout-2025-09-15", "entity_type": "fitness"},
            {"type": "entity", "name": "daily-note", "entity_type": "note"},
        ]
        
        # Save test records to 'test' context
        self.storage.save_database(test_records, "test")
        
    def teardown_method(self):
        """Clean up the temporary directory after tests."""
        if "MEMORY_FOLDER" in os.environ:
            del os.environ["MEMORY_FOLDER"]
        shutil.rmtree(self.temp_dir)
    
    def test_wildcard_pattern_star_prefix(self):
        """Test pattern matching with a wildcard prefix (*2025*)."""
        # Search for any entity with '2025' in the name
        results = self.storage.memory_search_nodes([], ["test"], "*2025*")
        
        # Verify that all entities with '2025' in the name were found
        assert "test" in results
        assert len(results["test"]) == 5
        
        # Check that all found records have '2025' in their name
        for record in results["test"]:
            assert "2025" in record["name"]
        
        # Verify that the 'daily-note' and 'work-2024-10-15' entities were not included
        for record in results["test"]:
            assert record["name"] != "daily-note"
            assert record["name"] != "work-2024-10-15"
    
    def test_wildcard_pattern_star_suffix(self):
        """Test pattern matching with a wildcard suffix (diet*)."""
        # Search for any entity with a name starting with 'diet'
        results = self.storage.memory_search_nodes([], ["test"], "diet*")
        
        # Verify that all entities with names starting with 'diet' were found
        assert "test" in results
        assert len(results["test"]) == 2
        
        # Check that all found records have names starting with 'diet'
        for record in results["test"]:
            assert record["name"].startswith("diet")
    
    def test_wildcard_pattern_specific_format(self):
        """Test pattern matching with a specific format (work-2025-09-*)."""
        # Search for work tasks from September 2025
        results = self.storage.memory_search_nodes([], ["test"], "work-2025-09-*")
        
        # Verify that only the matching work tasks were found
        assert "test" in results
        assert len(results["test"]) == 2
        
        # Check that all found records match the pattern
        for record in results["test"]:
            assert record["name"].startswith("work-2025-09-")
    
    def test_wildcard_pattern_with_keywords(self):
        """Test pattern matching combined with keyword filtering."""
        # Search for entities with '2025' in the name and containing 'health' keyword
        results = self.storage.memory_search_nodes(["health"], ["test"], "*2025*")
        
        # Verify that only health-related 2025 entities were found
        assert "test" in results
        assert len(results["test"]) == 2
        
        # Check that all found records have '2025' in their name and are health-related
        for record in results["test"]:
            assert "2025" in record["name"]
            assert record["entity_type"] == "health"
    
    def test_no_pattern_only_keywords(self):
        """Test that search still works with only keywords and no pattern."""
        # Search for entities containing 'fitness' keyword without a pattern
        results = self.storage.memory_search_nodes(["fitness"], ["test"])
        
        # Verify that only fitness-related entities were found
        assert "test" in results
        assert len(results["test"]) == 1
        assert results["test"][0]["name"] == "workout-2025-09-15"
    
    def test_empty_keywords_with_pattern(self):
        """Test that search works with an empty keywords list but a pattern."""
        # Search for entities with a specific pattern and no keywords
        results = self.storage.memory_search_nodes([], ["test"], "daily-*")
        
        # Verify that matching entities were found
        assert "test" in results
        assert len(results["test"]) == 1
        assert results["test"][0]["name"] == "daily-note"