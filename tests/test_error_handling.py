import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from storage import MemoryStorage, BM_GM_SAFETY_MARKER


class TestErrorHandling:
    """Test suite for error handling and recovery scenarios."""
    
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
    
    def test_corrupted_json(self):
        """Test handling of corrupted JSON in database files."""
        # Create a database with corrupted JSON
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity1"}) + '\n')
            f.write("This is not valid JSON\n")
            f.write(json.dumps({"type": "entity", "name": "Entity2"}) + '\n')
        
        # Load the database - should skip corrupted line
        records = self.storage.load_database()
        
        # Check that valid records were loaded
        assert len(records) == 2
        assert records[0]["name"] == "Entity1"
        assert records[1]["name"] == "Entity2"
    
    def test_missing_safety_marker(self):
        """Test handling of database files with missing safety marker."""
        # Create a database without the safety marker
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write(json.dumps({"type": "entity", "name": "Entity1"}) + '\n')
        
        # Attempting to load should raise a ValueError
        with pytest.raises(ValueError):
            self.storage.load_database()
    
    def test_incorrect_safety_marker(self):
        """Test handling of database files with incorrect safety marker."""
        # Create a database with incorrect safety marker
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write(json.dumps({"type": "_bm_gm", "source": "wrong-source"}) + '\n')
        
        # Attempting to load should raise a ValueError
        with pytest.raises(ValueError):
            self.storage.load_database()
    
    def test_permission_denied_simulation(self):
        """Test handling of permission denied errors (simulated)."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Create a read-only directory (simulating permission issues)
        readonly_dir = Path(self.temp_dir) / "readonly"
        readonly_dir.mkdir()
        
        # Point the storage to the read-only directory
        orig_dir = os.environ["MEMORY_FOLDER"]
        os.environ["MEMORY_FOLDER"] = str(readonly_dir)
        
        # Create a new storage instance
        readonly_storage = MemoryStorage()
        
        # We can't actually make it read-only in the test easily,
        # but we can at least verify the behavior with nonexistent files
        with pytest.raises(ValueError):
            readonly_storage.load_database()
        
        # Restore original directory
        os.environ["MEMORY_FOLDER"] = orig_dir
    
    def test_empty_records_list(self):
        """Test saving an empty records list."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Save an empty list of records
        self.storage.save_database([])
        
        # Load the records
        records = self.storage.load_database()
        
        # Check that an empty list was loaded
        assert isinstance(records, list)
        assert len(records) == 0
    
    def test_recovery_from_backup(self):
        """Test recovery from a backup file (simulated)."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Save some records
        original_records = [
            {"type": "entity", "name": "Entity1", "entityType": "test"},
            {"type": "entity", "name": "Entity2", "entityType": "test"}
        ]
        self.storage.save_database(original_records)
        
        # Simulate a corrupted file by writing invalid content
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write("Corrupted file content\n")
        
        # Create a backup file (as might happen in a real system)
        backup_path = Path(self.temp_dir) / "memory.jsonl.bak"
        with open(backup_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
            for record in original_records:
                f.write(json.dumps(record) + '\n')
        
        # Attempt to load the corrupted file should fail
        with pytest.raises(ValueError):
            self.storage.load_database()
        
        # Simulate recovery by copying backup to main file
        shutil.copy(backup_path, db_path)
        
        # Now loading should succeed
        recovered_records = self.storage.load_database()
        assert len(recovered_records) == len(original_records)
        assert recovered_records[0]["name"] == "Entity1"
        assert recovered_records[1]["name"] == "Entity2"
    
    def test_unexpected_data_types(self):
        """Test handling of unexpected data types in database files."""
        # Create a database with various unusual but valid JSON values
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity1", "value": None}) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity2", "value": 123}) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity3", "value": True}) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity4", "value": [1, "two", None]}) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Entity5", "value": {"nested": "object"}}) + '\n')
        
        # Load the database
        records = self.storage.load_database()
        
        # Check that all records were loaded correctly
        assert len(records) == 5
        assert records[0]["value"] is None
        assert records[1]["value"] == 123
        assert records[2]["value"] is True
        assert records[3]["value"] == [1, "two", None]
        assert records[4]["value"] == {"nested": "object"}