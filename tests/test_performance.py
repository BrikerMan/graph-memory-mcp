import os
import time
import tempfile
import shutil
import random
import string
from storage import MemoryStorage


class TestPerformance:
    """Test suite for performance and stress testing."""
    
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
    
    def generate_random_string(self, length=10):
        """Generate a random string of the specified length."""
        return ''.join(random.choice(string.ascii_letters) for _ in range(length))
    
    def generate_entity_record(self, name):
        """Generate an entity record with the specified name."""
        return {
            "type": "entity",
            "name": name,
            "entityType": random.choice(["person", "place", "thing", "concept"]),
            "observations": [
                self.generate_random_string(50) for _ in range(random.randint(0, 5))
            ]
        }
    
    def generate_relation_record(self, source, target):
        """Generate a relation record between the specified source and target."""
        return {
            "type": "relation",
            "source": source,
            "target": target,
            "relationType": random.choice(["knows", "contains", "near", "related"]),
            "directed": random.choice([True, False])
        }
    
    def test_bulk_save_load(self):
        """Test saving and loading a large number of records."""
        # Define test sizes
        entity_counts = [10, 100, 1000]
        relation_ratios = [0.5, 1, 2]  # Relations per entity
        
        for entity_count in entity_counts:
            for relation_ratio in relation_ratios:
                # Calculate relation count based on ratio
                relation_count = int(entity_count * relation_ratio)
                
                # Generate entities
                entities = []
                for i in range(entity_count):
                    name = f"Entity{i}"
                    entities.append(self.generate_entity_record(name))
                
                # Generate relations
                relations = []
                entity_names = [e["name"] for e in entities]
                for i in range(relation_count):
                    source = random.choice(entity_names)
                    target = random.choice(entity_names)
                    relations.append(self.generate_relation_record(source, target))
                
                # Combine records
                records = entities + relations
                
                # Measure save time
                save_start = time.time()
                self.storage.save_database(records, f"test_{entity_count}_{relation_ratio}")
                save_time = time.time() - save_start
                
                # Measure load time
                load_start = time.time()
                loaded_records = self.storage.load_database(f"test_{entity_count}_{relation_ratio}")
                load_time = time.time() - load_start
                
                # Verify record count
                assert len(loaded_records) == len(records)
                
                # Print performance metrics
                print(f"\nPerformance with {entity_count} entities and {relation_count} relations:")
                print(f"  Save time: {save_time:.4f} seconds")
                print(f"  Load time: {load_time:.4f} seconds")
                print(f"  Records per second (save): {len(records)/save_time:.1f}")
                print(f"  Records per second (load): {len(records)/load_time:.1f}")
    
    def test_many_contexts(self):
        """Test creating and listing many contexts."""
        # Define number of contexts to create
        context_counts = [10, 50, 100]
        
        for context_count in context_counts:
            # Create a record for each context
            for i in range(context_count):
                context_name = f"context_{i}"
                self.storage.save_database([self.generate_entity_record(f"Entity_{i}")], context_name)
            
            # Measure list contexts time
            list_start = time.time()
            contexts = self.storage.list_contexts()
            list_time = time.time() - list_start
            
            # Verify context count (add 1 for 'main')
            assert len(contexts) == context_count + 1
            
            # Print performance metrics
            print(f"\nPerformance with {context_count} contexts:")
            print(f"  List contexts time: {list_time:.4f} seconds")
            print(f"  Contexts per second: {len(contexts)/list_time:.1f}")
            
            # Clean up contexts for next test
            shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir)
            self.storage.initialize_storage()
    
    def test_large_observations(self):
        """Test storing and loading entities with large observation texts."""
        # Define observation sizes
        observation_sizes = [1000, 10000, 100000]
        
        for size in observation_sizes:
            # Create an entity with a large observation
            entity = self.generate_entity_record("LargeEntity")
            entity["observations"] = [self.generate_random_string(size)]
            
            # Save and load the entity
            save_start = time.time()
            self.storage.save_database([entity], f"large_{size}")
            save_time = time.time() - save_start
            
            load_start = time.time()
            loaded_records = self.storage.load_database(f"large_{size}")
            load_time = time.time() - load_start
            
            # Verify the observation was loaded correctly
            assert len(loaded_records) == 1
            assert len(loaded_records[0]["observations"]) == 1
            assert len(loaded_records[0]["observations"][0]) == size
            
            # Print performance metrics
            print(f"\nPerformance with {size} character observation:")
            print(f"  Save time: {save_time:.4f} seconds")
            print(f"  Load time: {load_time:.4f} seconds")
            print(f"  Characters per second (save): {size/save_time:.1f}")
            print(f"  Characters per second (load): {size/load_time:.1f}")
    
    def test_repeated_operations(self):
        """Test repeatedly saving and loading the same database."""
        # Create initial records
        records = [self.generate_entity_record(f"Entity{i}") for i in range(100)]
        
        # Perform multiple save/load cycles
        cycles = 10
        total_save_time = 0
        total_load_time = 0
        
        for i in range(cycles):
            # Add one more record each cycle
            records.append(self.generate_entity_record(f"NewEntity{i}"))
            
            # Save the updated records
            save_start = time.time()
            self.storage.save_database(records)
            save_time = time.time() - save_start
            total_save_time += save_time
            
            # Load the records
            load_start = time.time()
            loaded_records = self.storage.load_database()
            load_time = time.time() - load_start
            total_load_time += load_time
            
            # Verify record count
            assert len(loaded_records) == len(records)
        
        # Print performance metrics
        print(f"\nPerformance over {cycles} save/load cycles:")
        print(f"  Average save time: {total_save_time/cycles:.4f} seconds")
        print(f"  Average load time: {total_load_time/cycles:.4f} seconds")
        print(f"  Final record count: {len(records)}")