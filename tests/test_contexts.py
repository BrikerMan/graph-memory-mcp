import os
import tempfile
import shutil
import pytest
from storage import MemoryStorage


class TestMultipleContexts:
    """Test suite for operations across multiple contexts."""
    
    def setup_method(self):
        """Set up a temporary directory with multiple contexts."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["MEMORY_FOLDER"] = self.temp_dir
        self.storage = MemoryStorage()
        self.storage.initialize_storage()
        
        # Create test data for different contexts
        self.main_records = [
            {"type": "entity", "name": "MainEntity1", "entityType": "concept"},
            {"type": "entity", "name": "MainEntity2", "entityType": "concept"},
        ]
        
        self.work_records = [
            {"type": "entity", "name": "WorkEntity1", "entityType": "project"},
            {"type": "entity", "name": "WorkEntity2", "entityType": "colleague"},
            {"type": "relation", "source": "WorkEntity1", "target": "WorkEntity2", "relationType": "involves"}
        ]
        
        self.personal_records = [
            {"type": "entity", "name": "PersonalEntity1", "entityType": "friend"},
            {"type": "entity", "name": "PersonalEntity2", "entityType": "hobby"},
            {"type": "relation", "source": "PersonalEntity1", "target": "PersonalEntity2", "relationType": "enjoys"}
        ]
        
        # Save test data to different contexts
        self.storage.save_database(self.main_records)
        self.storage.save_database(self.work_records, "work")
        self.storage.save_database(self.personal_records, "personal")
    
    def teardown_method(self):
        """Clean up the temporary directory after tests."""
        if "MEMORY_FOLDER" in os.environ:
            del os.environ["MEMORY_FOLDER"]
        shutil.rmtree(self.temp_dir)
    
    def test_load_specific_context(self):
        """Test loading records from specific contexts."""
        # Test loading main context
        main_loaded = self.storage.load_database()
        assert len(main_loaded) == len(self.main_records)
        assert [r["name"] for r in main_loaded] == ["MainEntity1", "MainEntity2"]
        
        # Test loading work context
        work_loaded = self.storage.load_database("work")
        assert len(work_loaded) == len(self.work_records)
        assert [r["name"] for r in work_loaded if r.get("type") == "entity"] == ["WorkEntity1", "WorkEntity2"]
        
        # Test loading personal context
        personal_loaded = self.storage.load_database("personal")
        assert len(personal_loaded) == len(self.personal_records)
        assert [r["name"] for r in personal_loaded if r.get("type") == "entity"] == ["PersonalEntity1", "PersonalEntity2"]
    
    def test_list_all_contexts(self):
        """Test listing all available contexts."""
        contexts = self.storage.list_contexts()
        assert sorted(contexts) == sorted(["main", "work", "personal"])
    
    def test_update_specific_context(self):
        """Test updating records in a specific context."""
        # Update work context
        updated_work_records = self.storage.load_database("work")
        updated_work_records.append({"type": "entity", "name": "WorkEntity3", "entityType": "task"})
        self.storage.save_database(updated_work_records, "work")
        
        # Check that only work context was updated
        assert len(self.storage.load_database()) == len(self.main_records)
        assert len(self.storage.load_database("work")) == len(self.work_records) + 1
        assert len(self.storage.load_database("personal")) == len(self.personal_records)
        
        # Verify new entity exists in work context
        work_entities = [r["name"] for r in self.storage.load_database("work") if r.get("type") == "entity"]
        assert "WorkEntity3" in work_entities
    
    def test_nonexistent_context(self):
        """Test loading a nonexistent context."""
        with pytest.raises(ValueError):
            self.storage.load_database("nonexistent")


class TestEdgeCases:
    """Test suite for edge cases in storage operations."""
    
    def setup_method(self):
        """Set up a temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["MEMORY_FOLDER"] = self.temp_dir
        self.storage = MemoryStorage()
    
    def teardown_method(self):
        """Clean up the temporary directory after tests."""
        if "MEMORY_FOLDER" in os.environ:
            del os.environ["MEMORY_FOLDER"]
        shutil.rmtree(self.temp_dir)
    
    def test_empty_database(self):
        """Test operations on an empty database."""
        # Initialize storage with empty main database
        self.storage.initialize_storage()
        
        # Load the empty database
        records = self.storage.load_database()
        assert len(records) == 0
        
        # Save and load an empty list of records
        self.storage.save_database([])
        records = self.storage.load_database()
        assert len(records) == 0
    
    def test_special_characters_in_context_name(self):
        """Test using special characters in context names."""
        # Create contexts with special characters
        special_contexts = ["test-hyphen", "test_underscore", "test.dot", "test space"]
        
        for context in special_contexts:
            self.storage.save_database([{"type": "entity", "name": f"Entity-{context}", "entityType": "test"}], context)
        
        # Check that all contexts were created correctly
        for context in special_contexts:
            records = self.storage.load_database(context)
            assert len(records) == 1
            assert records[0]["name"] == f"Entity-{context}"
        
        # Check that all contexts are listed
        contexts = self.storage.list_contexts()
        for context in special_contexts:
            assert context in contexts
    
    def test_unicode_in_records(self):
        """Test storing and loading records with Unicode characters."""
        # Create records with Unicode characters
        unicode_records = [
            {"type": "entity", "name": "名字", "entityType": "person"},
            {"type": "entity", "name": "🚀", "entityType": "emoji"},
            {"type": "relation", "source": "名字", "target": "🚀", "relationType": "likes"}
        ]
        
        # Save and load records
        self.storage.initialize_storage()
        self.storage.save_database(unicode_records)
        loaded_records = self.storage.load_database()
        
        # Check that records were loaded correctly
        assert len(loaded_records) == len(unicode_records)
        assert loaded_records[0]["name"] == "名字"
        assert loaded_records[1]["name"] == "🚀"
        assert loaded_records[2]["source"] == "名字"
        assert loaded_records[2]["target"] == "🚀"
    
    def test_concurrent_access_simulation(self):
        """Test simulating concurrent access by creating multiple storage instances."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Create initial records
        initial_records = [{"type": "entity", "name": "Entity1", "entityType": "test"}]
        self.storage.save_database(initial_records)
        
        # Create a second storage instance (simulating another process)
        storage2 = MemoryStorage()
        
        # Both instances should see the same data
        records1 = self.storage.load_database()
        records2 = storage2.load_database()
        
        assert len(records1) == 1
        assert len(records2) == 1
        assert records1[0]["name"] == "Entity1"
        assert records2[0]["name"] == "Entity1"
        
        # Update from the second instance
        records2.append({"type": "entity", "name": "Entity2", "entityType": "test"})
        storage2.save_database(records2)
        
        # First instance should see the update
        updated_records = self.storage.load_database()
        assert len(updated_records) == 2
        assert [r["name"] for r in updated_records] == ["Entity1", "Entity2"]