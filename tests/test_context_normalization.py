import os
import tempfile
import shutil
from src.storage import MemoryStorage


class TestContextNormalization:
    """Test suite for the context normalization functionality in MemoryStorage."""
    
    def setup_method(self):
        """Set up a temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["MEMORY_FOLDER"] = self.temp_dir
        self.storage = MemoryStorage()
        self.storage.initialize_storage()
        
    def teardown_method(self):
        """Clean up the temporary directory after tests."""
        if "MEMORY_FOLDER" in os.environ:
            del os.environ["MEMORY_FOLDER"]
        shutil.rmtree(self.temp_dir)
    
    def test_context_normalization(self):
        """Test that 'main', 'default', and empty string all use the main database."""
        # Create test entity in main database
        entity = {"type": "entity", "name": "test-entity", "entity_type": "test"}
        self.storage.memory_create_entities([entity], "main")
        
        # Verify entity exists in main database
        main_entity = self.storage.memory_read_entity("test-entity", "main")
        assert main_entity is not None
        assert main_entity["name"] == "test-entity"
        
        # Test with 'default' context
        default_entity = self.storage.memory_read_entity("test-entity", "default")
        assert default_entity is not None
        assert default_entity["name"] == "test-entity"
        
        # Test with empty string context
        empty_entity = self.storage.memory_read_entity("test-entity", "")
        assert empty_entity is not None
        assert empty_entity["name"] == "test-entity"
        
        # Test with None context (should default to main)
        none_entity = self.storage.memory_read_entity("test-entity", None)
        assert none_entity is not None
        assert none_entity["name"] == "test-entity"
        
    def test_database_paths(self):
        """Test that get_database_path returns the main database path for normalized contexts."""
        # Get the main database path
        main_path = self.storage.get_database_path("main")
        
        # Get paths for other context values
        default_path = self.storage.get_database_path("default")
        empty_path = self.storage.get_database_path("")
        none_path = self.storage.get_database_path(None)
        
        # All should point to the same file
        assert main_path == default_path
        assert main_path == empty_path
        assert main_path == none_path
        
        # Should be different from a custom context
        custom_path = self.storage.get_database_path("custom")
        assert main_path != custom_path