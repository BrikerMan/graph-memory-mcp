import os
import json
import tempfile
import shutil
from pathlib import Path
from storage import MemoryStorage, BM_GM_SAFETY_MARKER


class TestMemoryStorage:
    """Test suite for the MemoryStorage class."""
    
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
    
    def test_get_storage_path_with_env_var(self):
        """Test that storage path uses MEMORY_FOLDER environment variable."""
        assert self.storage.get_storage_path() == Path(self.temp_dir)
    
    def test_get_storage_path_default(self):
        """Test that storage path defaults to ~/.bm if MEMORY_FOLDER is not set."""
        del os.environ["MEMORY_FOLDER"]
        storage = MemoryStorage()  # Create a new instance after removing the env var
        assert storage.get_storage_path() == Path.home() / ".bm"
    
    def test_initialize_storage(self):
        """Test that initialize_storage creates the directory and main database."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Check that the directory was created
        assert Path(self.temp_dir).exists()
        
        # Check that the main database was created
        main_db_path = Path(self.temp_dir) / "memory.jsonl"
        assert main_db_path.exists()
        
        # Check that the main database has the safety marker
        with open(main_db_path, 'r') as f:
            first_line = f.readline().strip()
            marker = json.loads(first_line)
            assert marker.get("type") == "_bm_gm"
            assert marker.get("source") == "brikerman-graph-memory-mcp"
    
    def test_validate_database_file(self):
        """Test that _validate_database_file correctly validates a database file."""
        # Create a valid database file
        valid_db_path = Path(self.temp_dir) / "valid.jsonl"
        with open(valid_db_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
        
        # Create an invalid database file (no safety marker)
        invalid_db_path = Path(self.temp_dir) / "invalid.jsonl"
        with open(invalid_db_path, 'w') as f:
            f.write(json.dumps({"type": "not_bm_gm"}) + '\n')
        
        # Create an empty file
        empty_db_path = Path(self.temp_dir) / "empty.jsonl"
        with open(empty_db_path, 'w') as f:
            pass
        
        # Test validation
        assert self.storage._validate_database_file(valid_db_path) is True
        assert self.storage._validate_database_file(invalid_db_path) is False
        assert self.storage._validate_database_file(empty_db_path) is False
        assert self.storage._validate_database_file(Path(self.temp_dir) / "nonexistent.jsonl") is False
    
    def test_get_database_path(self):
        """Test that get_database_path returns the correct paths."""
        # Test main database path
        assert self.storage.get_database_path() == Path(self.temp_dir) / "memory.jsonl"
        assert self.storage.get_database_path("main") == Path(self.temp_dir) / "memory.jsonl"
        
        # Test context database path
        assert self.storage.get_database_path("test") == Path(self.temp_dir) / "memory-test.jsonl"
    
    def test_load_save_database(self):
        """Test loading and saving database records."""
        # Create test records
        test_records = [
            {"type": "entity", "name": "Person1", "entityType": "person"},
            {"type": "entity", "name": "Person2", "entityType": "person"},
            {"type": "relation", "source": "Person1", "target": "Person2", "relationType": "knows"}
        ]
        
        # Initialize storage and save records
        self.storage.initialize_storage()
        self.storage.save_database(test_records)
        
        # Load records and check they match
        loaded_records = self.storage.load_database()
        assert len(loaded_records) == len(test_records)
        for i, record in enumerate(test_records):
            assert loaded_records[i] == record
    
    def test_load_database_invalid_file(self):
        """Test that load_database raises ValueError for invalid files."""
        # Create an invalid database file
        invalid_db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(invalid_db_path, 'w') as f:
            f.write(json.dumps({"type": "not_bm_gm"}) + '\n')
        
        # Attempt to load the invalid file
        try:
            self.storage.load_database()
            assert False, "Expected ValueError was not raised"
        except ValueError:
            # This is expected
            pass
    
    def test_list_contexts(self):
        """Test that list_contexts returns all available contexts."""
        # Initialize storage
        self.storage.initialize_storage()
        
        # Create some context databases
        self.storage.save_database([], "work")
        self.storage.save_database([], "personal")
        
        # Create an invalid context database (no safety marker)
        invalid_db_path = Path(self.temp_dir) / "memory-invalid.jsonl"
        with open(invalid_db_path, 'w') as f:
            f.write(json.dumps({"type": "not_bm_gm"}) + '\n')
        
        # List contexts
        contexts = self.storage.list_contexts()
        
        # Check that all valid contexts are listed
        assert "main" in contexts
        assert "work" in contexts
        assert "personal" in contexts
        
        # Check that the invalid context is not listed
        assert "invalid" not in contexts
        
    def test_save_database_creates_directory(self):
        """Test that save_database creates the directory if it doesn't exist."""
        # Remove the temp directory
        shutil.rmtree(self.temp_dir)
        
        # Save records (should create the directory)
        self.storage.save_database([])
        
        # Check that the directory was created
        assert Path(self.temp_dir).exists()
        
        # Check that the main database was created
        main_db_path = Path(self.temp_dir) / "memory.jsonl"
        assert main_db_path.exists()
    
    def test_load_database_with_invalid_json(self):
        """Test that load_database handles invalid JSON lines gracefully."""
        # Create a database with an invalid JSON line
        db_path = Path(self.temp_dir) / "memory.jsonl"
        with open(db_path, 'w') as f:
            f.write(json.dumps(BM_GM_SAFETY_MARKER) + '\n')
            f.write(json.dumps({"type": "entity", "name": "Valid"}) + '\n')
            f.write("This is not valid JSON\n")
            f.write(json.dumps({"type": "entity", "name": "AlsoValid"}) + '\n')
        
        # Load the database
        records = self.storage.load_database()
        
        # Check that valid records were loaded
        assert len(records) == 2
        assert records[0]["name"] == "Valid"
        assert records[1]["name"] == "AlsoValid"