# bm-graph-memory-mcp

**A persistent, indexed knowledge graph for AI agents, designed for MCP-compatible platforms.**

This project, Brikerman Graph Memory (bm-graph-memory), provides a persistent memory layer for AI models. It allows an AI to build and query a knowledge graph composed of entities, relationships, and observations. The system is designed around a core "index" database that ensures the AI always has access to its most critical information.

---

## Core Concepts

### The `main` Database: The System's Core Index
The entire system revolves around the **`main`** database. It is not just a general-purpose memory; it has a specific and critical function.

- **Role**: The `main` database acts as the **core index and routing table** for your entire memory system.
- **Contents**: It should contain only two types of information:
    1.  **Routing Information**: A manifest of all other contexts that exist (e.g., `work`, `personal`). This helps the AI know what other specialized memories it can query.
    2.  **Critical Data**: A very small amount of absolutely essential, high-level information that the AI must always be aware of.
- **Constant Visibility**: **The *entire contents* of the `main` database are automatically appended to the results of *every* search operation.** Whether you search globally or within a specific context, you always get the full `main` database back, ensuring the AI never loses sight of its core index.

### Contexts: Specialized Memories
To keep information organized, you can use `context`s. A context is a separate memory file for a specific topic.

- **Examples**: `work`, `personal`, `project-alpha`.
- **Primary Use**: Store detailed, topic-specific information in a named context. This keeps the `main` database clean and focused on its core indexing role.

### Storage Location
The system determines where to store and retrieve files based on the `MEMORY_FOLDER` environment variable:

- If `MEMORY_FOLDER` is set, all memory files will be stored in that location.
- If `MEMORY_FOLDER` is not set, the system defaults to `~/.bm` in the user's home directory.

### The `bm_gm` Safety System
A consistent naming convention ensures clarity and safety. `bm_gm` stands for **Brikerman Graph Memory**.

- **`.bm` directories**: Identifies a folder as a Brikerman Memory storage location.
- **`bm_gm_` tool prefixes**: Groups all memory functions together for the AI.
- **`_bm_gm` safety marker**: The first line of every memory file is `{"type":"_bm_gm","source":"brikerman-graph-memory-mcp"}`. The system will refuse to write to any file that doesn't start with this marker, preventing data corruption.

## Available AI Tools (`bm_gm_*`)

The AI interacts with its memory using the following tools.

### Core Tools
- `memory_create_entities`: Adds new entities (like people, places, or concepts) to the knowledge graph.
- `memory_create_relations`: Creates a labeled link between two existing entities.
- `memory_add_observations`: Adds a new piece of text information to an existing entity.
- `memory_search_nodes`: Searches for information using keywords. **The results will always include the full contents of the `main` database.**
- `memory_read_graph`: Dumps the entire content of one or more databases. **The results will always include the full contents of the `main` database.**

### Management & Deletion Tools
- `memory_list_databases`: Shows all available memory databases (contexts).
- `memory_delete_entities`: Removes entities from the graph.
- `memory_delete_relations`: Removes specific relationships between entities.
- `memory_delete_observations`: Removes specific observations from an entity.

### Common Parameters
- `context` (string): The named database to target (e.g., `work`). If not provided, the operation targets the `main` database.


## File Organization Example

**MEMORY_FOLDER directory:**
```tree
/path/to/memory/folder/
├── memory.jsonl           # The 'main' Database (Core Index)
├── memory-work.jsonl      # Work Context
└── memory-personal.jsonl  # Personal Context
```