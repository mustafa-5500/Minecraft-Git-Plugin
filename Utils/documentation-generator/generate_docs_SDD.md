# generate_docs.py — Software Detailed Design

> **Usage Documentation:** [generate_docs.md](./generate_docs.md)  
> **Source File:** [generate_docs.py](./generate_docs.py)

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Imports](#2-imports)
- [3. Data Models](#3-data-models)
- [4. Parsing Pipeline](#4-parsing-pipeline)
- [5. Type Cross-Referencing System](#5-type-cross-referencing-system)
- [6. Document Generation](#6-document-generation)
- [7. Merge Logic](#7-merge-logic)
- [8. Directory Traversal & Orchestration](#8-directory-traversal--orchestration)
- [9. CLI Entry Point](#9-cli-entry-point)
- [10. Design Decisions](#10-design-decisions)
- [11. Dependencies](#11-dependencies)
- [12. Known Limitations](#12-known-limitations)

---

## 1. Overview

`generate_docs.py` is a standalone Python utility that parses Java source files using regex-based extraction and generates structured Markdown documentation templates. It produces two documentation files per Java class: an API reference and a Software Detailed Design document. The script walks the source directory tree recursively, mirrors the folder structure in the output directory, and populates templates with extracted metadata (class names, fields, methods, imports, annotations). When documentation already exists, the script operates in merge mode — appending new methods/fields without overwriting existing content. All output passes through an inline type linking system that converts backtick-wrapped type names into clickable cross-references.

---

## 2. Imports

```python
import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
```

| Import | Purpose |
|--------|---------|
| `os` | File system operations: path resolution, directory walking, existence checks |
| `re` | Regular expression engine for parsing Java source code and inline type detection |
| `sys` | `sys.exit()` for error termination |
| `argparse` | CLI argument parsing with help generation |
| `Path` | Object-oriented path manipulation (available but primarily `os.path` is used) |
| `dataclass` | Declarative data classes for structured parse results |
| `field` | Default factory for mutable dataclass fields (lists) |
| `List`, `Optional` | Type annotations for clarity |

---

## 3. Data Models

### 3.1 `MethodInfo`

```python
@dataclass
class MethodInfo:
    name: str
    signature: str
    return_type: str
    parameters: List[tuple]
    annotations: List[str]
    access: str
    is_static: bool
    is_constructor: bool
```

Represents a single method or constructor extracted from a Java file.

| Field | Description |
|-------|-------------|
| `name` | Method identifier (or class name for constructors) |
| `signature` | Full reconstructed signature string for display in code blocks |
| `return_type` | Return type string (empty for constructors) |
| `parameters` | List of `(type, name)` tuples parsed from the parameter list |
| `annotations` | List of annotation strings (e.g., `"@Override"`) |
| `access` | Access modifier: `"public"`, `"private"`, or `"protected"` |
| `is_static` | Whether the method is declared `static` |
| `is_constructor` | Distinguishes constructors from regular methods |

### 3.2 `FieldInfo`

```python
@dataclass
class FieldInfo:
    name: str
    type: str
    access: str
    is_static: bool
    is_final: bool
```

Represents a class-level field declaration.

### 3.3 `JavaClassInfo`

```python
@dataclass
class JavaClassInfo:
    name: str
    file_name: str
    package: str
    imports: List[str]
    class_declaration: str
    fields: List[FieldInfo]
    methods: List[MethodInfo]
    extends_class: Optional[str]
    implements: List[str]
    javadoc: Optional[str]
```

Aggregate result of parsing a single Java file. Contains all metadata needed to generate both documentation templates.

---

## 4. Parsing Pipeline

### 4.1 `parse_java_file(file_path) → Optional[JavaClassInfo]`

The main parsing entry point. Reads the file content and delegates to sub-parsers.

**Steps:**
1. Read file with UTF-8 encoding (returns `None` on I/O or encoding errors)
2. Extract package declaration via regex: `^package\s+([\w.]+)\s*;`
3. Extract all import statements via regex: `^import\s+([\w.*]+)\s*;`
4. Locate the class/interface/enum declaration via a compound regex matching access modifiers, `extends`, and `implements` clauses
5. Extract class-level Javadoc by searching backward from the class declaration for a `/** ... */` block
6. Delegate to `extract_fields()` for field parsing
7. Delegate to `extract_methods()` for method/constructor parsing
8. Assemble and return a `JavaClassInfo` instance

**Class Declaration Regex:**
```
public\s+(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+
(\w+)(?:\s+extends\s+([\w<>,\s]+?))?(?:\s+implements\s+([\w<>,\s]+?))?\s*\{
```

This handles standard Java class declarations including abstract classes, final classes, interfaces, and enums with optional inheritance and interface implementation.

### 4.2 `extract_fields(content, class_body_start) → List[FieldInfo]`

Extracts field declarations from the region between the class opening brace and the first method declaration.

**Strategy:**
- Finds the first method signature after `class_body_start` to bound the search region
- If no method is found, searches the first 500 characters after the class body start
- Matches lines of the form: `[access] [static] [final] Type name [= ...| ;]`
- Filters out false positives where the "type" is a keyword (`return`, `if`, `for`, etc.)

### 4.3 `extract_methods(content, class_name) → List[MethodInfo]`

Extracts all method and constructor signatures from the entire file content.

**Constructor Detection:**
- Uses a separate regex that matches `[access] ClassName(params) {`
- The class name is escaped with `re.escape()` to handle special characters safely
- Constructors are processed first, then excluded from the general method regex by name comparison

**Method Detection Regex:**
```
(?:(@\w+(?:\([^)]*\))?)\s+)?          # optional annotation
(public|private|protected)\s+          # access modifier
(static\s+)?                           # optional static
(?:synchronized\s+)?                   # optional synchronized
([\w<>\[\],?\s]+?)\s+                  # return type
(\w+)\s*                               # method name
\(([^)]*)\)\s*                         # parameters
(?:throws\s+[\w,\s]+)?\s*\{           # optional throws clause
```

**Limitations:**
- Only captures the first annotation per method
- Does not handle multi-line parameter lists (parameters must be on one line)
- Does not parse method bodies

### 4.4 `parse_parameters(params_raw) → List[tuple]`

Splits a comma-separated parameter string into `(type, name)` tuples.

- Strips parameter annotations (e.g., `@NotNull`)
- Uses `rsplit(" ", 1)` to separate type from name (handles generic types with spaces like `Map<String, List<Integer>>`)

---

## 5. Type Cross-Referencing System

### 5.1 `build_type_doc_map(source_dir, docs_output_dir) → dict`

Builds a mapping of `class_name → absolute_doc_path` for all Java files in the source tree.

**Algorithm:**
1. Walk the source directory recursively
2. For each `.java` file, derive the class name (filename without extension)
3. Compute the expected documentation file path (mirroring the directory structure)
4. Store the mapping: `{"SelectionManager": "C:/.../Documentation/manager/SelectionManager.md"}`

This map is used by all linking functions to resolve type references.

### 5.2 `resolve_type_link(type_str, type_doc_map, current_doc_dir, current_class) → str`

Resolves a type string (used in structured positions like parameter tables and return types) to a markdown link if documentation exists.

**Steps:**
1. Strip generics (`<...>`) and array brackets (`[]`) to find the base type
2. Skip self-references (don't link a class to its own doc)
3. Look up the base type in `type_doc_map`
4. If found, compute the relative path from the current doc directory
5. Return `` [`type_str`](relative/path.md) `` or plain `` `type_str` `` if not found

### 5.3 `linkify_inline_types(text, type_doc_map, current_doc_dir, current_class) → str`

Scans a single line of text for backtick-wrapped type references and converts them to markdown links.

**Regex:**
```python
r"(?<!\[)`([A-Z][\w<>\[\],\s]*?)`(?!\])"
```

- **Negative lookbehind `(?<!\[)`** — Skips types already inside a markdown link `[`Type`](...)`
- **Negative lookahead `(?!\])`** — Further guards against double-linking
- **Match group** — Captures type names starting with an uppercase letter (convention for Java classes)

**Replacement logic:**
1. Strip generics/arrays to find the base type
2. Skip self-references
3. Look up in `type_doc_map` and compute relative path
4. Wrap as `` [`TypeName`](path.md) ``

### 5.4 `linkify_content(content, type_doc_map, current_doc_dir, current_class) → str`

Applies `linkify_inline_types` to all lines in the content while **skipping code blocks** (delimited by `` ``` ``).

This function is the final pass applied to all generated and merged output before writing to disk.

---

## 6. Document Generation

### 6.1 `generate_api_doc(class_info, relative_source_path, type_doc_map, doc_dir) → str`

Produces the API reference Markdown file content.

**Template Structure:**
```
# ClassName

> **Software Detailed Documentation:** [ClassName_SDD.md](./ClassName_SDD.md)
> **Source File:** [FileName.java](relative/path/to/source)

[Description or TODO placeholder]

---

## Table of Contents

**Fields:**
- `fieldName` ([`Type`](path/to/Type.md)) — TODO: describe field

**Functions:**
- [methodName](#methodname)

---

## methodName

### Signature
```java
[annotations]
[full signature]
```

### Description
TODO: ...

### Parameters
| Name | Type | Description |
...

### Returns
[`ReturnType`](path/to/ReturnType.md) — TODO: ...

---

## See Also

- **Software Detailed Design:** [ClassName_SDD.md](./ClassName_SDD.md)
```

**Header generation:** The top block is produced by `build_api_header()`, which standardizes the title and the two metadata links.

**Ordering:** Public methods are listed first in the table of contents, followed by private/protected methods. Duplicate names are deduplicated in the TOC.

**Type linking:** Field types, parameter types, and return types are linked via `resolve_type_link`. The final output passes through `linkify_content` for inline linking of all remaining backtick references.

### 6.2 `generate_sdd_doc(class_info, relative_source_path, api_doc_filename, type_doc_map, doc_dir) → str`

Produces the Software Detailed Design Markdown file content.

**Template Structure:**
```
# ClassName — Software Detailed Design

> **API Documentation:** [ClassName.md](./ClassName.md)
> **Source File:** [FileName.java](relative/path)

---

## 1. Overview
## 2. Package Declaration & Imports
## 3. Class Declaration
## 4. Instance Fields
## 5+. [One section per method]
```

**Section Numbering:** Sections are auto-numbered sequentially. If there are no fields, the fields section is omitted and method sections start at 4.

**Type linking:** The final output passes through `linkify_content` for inline backtick reference linking.

### 6.3 `generate_api_method_section(method, type_doc_map, doc_dir, class_name) → str`

Generates a single method section for the API doc (used by both full generation and merge mode).

### 6.4 `generate_sdd_method_section(method, section_num) → str`

Generates a single method section for the SDD doc (used by both full generation and merge mode).

---

## 7. Merge Logic

### 7.1 `parse_existing_api_doc(file_path) → dict`

Parses an existing API `.md` file and extracts structural metadata.

**Returns:**
| Key | Type | Description |
|-----|------|-------------|
| `content` | `str` | Full file content |
| `documented_methods` | `set` | Method names found as `## heading` entries |
| `documented_fields` | `set` | Field names found in the Fields section |
| `toc_end_line` | `int` | Line index where the Functions TOC ends |
| `methods_start_line` | `int` | Line index where method sections begin |
| `see_also_line` | `int` | Line index of the See Also section (or `-1`) |
| `lines` | `list` | All lines as a list |

### 7.2 `parse_existing_sdd_doc(file_path) → dict`

Parses an existing SDD `_SDD.md` file and extracts documented method information.

**Detection methods:**
1. Numbered section headings: `## 5. \`methodName()\``
2. Method signatures in code blocks (handles methods grouped in a single section)

**Returns:**
| Key | Type | Description |
|-----|------|-------------|
| `content` | `str` | Full file content |
| `documented_methods` | `set` | Method names found via headings or signatures |
| `last_section_num` | `int` | Highest section number found |
| `lines` | `list` | All lines as a list |

### 7.3 `merge_api_doc(existing_path, class_info, type_doc_map, doc_dir, relative_source_path) → str | None`

Merges new methods and fields into an existing API doc.

**Algorithm:**
1. Parse the existing doc to find already-documented methods and fields
2. Normalize the top API header via `normalize_api_header(...)` so legacy docs are rewritten to the current header format
3. Identify new methods/fields present in source but missing from docs
4. If nothing new and the header is already current, return `None`
5. Insert new fields after the last existing field entry
6. Insert new TOC entries after the last existing TOC line (deduplicated)
7. Extract the See Also section (if present) from its current position
8. Append new method sections (via `generate_api_method_section`)
9. Re-append See Also at the very end with clean separator handling

This is why existing API docs can be updated even when no new methods were added: the merge step now also serves as the migration path for the API header format.

### 7.4 `merge_sdd_doc(existing_path, class_info) → str | None`

Merges new method sections into an existing SDD doc.

**Algorithm:**
1. Parse existing doc to find documented methods (by heading or signature)
2. Identify methods in source not yet in the doc
3. If nothing new, return `None`
4. Assign section numbers continuing from `last_section_num + 1`
5. Append new sections at the end of the file

---

## 8. Directory Traversal & Orchestration

### 8.1 `process_source_directory(source_dir, docs_output_dir, overwrite) → (int, int)`

Orchestrates the full generation pipeline.

**Algorithm:**
1. Convert paths to absolute
2. Build the `type_doc_map` for cross-referencing
3. Walk the source directory with `os.walk()`
4. For each `.java` file, determine the processing mode:

| Condition | Mode | Action |
|-----------|------|--------|
| `--overwrite` flag set | Overwrite | Full regeneration of both files |
| Both `.md` and `_SDD.md` exist | Merge | Add missing methods/fields, re-linkify |
| One or both files missing | Create | Generate missing file(s) |

5. In merge mode, regardless of whether new sections are added, both files receive a re-linkification pass (ensuring all backtick type references are linked)
6. Return counts of generated and skipped file pairs

### 8.2 `compute_relative_source_path(source_file, source_root, doc_file_dir) → str`

Computes the relative path from a documentation file's directory to the corresponding source file. Uses `os.path.relpath()` and normalizes backslashes to forward slashes for Markdown link compatibility.

---

## 9. CLI Entry Point

### `main()`

1. Defines the argument parser with two positional args and one optional flag
2. Validates that `source_dir` exists as a directory
3. Prints configuration summary
4. Calls `process_source_directory()`
5. Prints final statistics

**Exit Codes:**
- `0` — Success
- `1` — Invalid source directory path

---

## 10. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Regex-based parsing (not AST) | Zero external dependencies; sufficient for signature extraction without needing a full Java parser |
| Merge-by-default behavior | Prevents accidental loss of manually-written documentation while keeping docs in sync with source |
| Normalized API header helper | Keeps newly generated and previously existing API docs on the same top-level format |
| Inline type linking as a final pass | Decouples link generation from template logic; applies uniformly to all output paths (generate, merge, re-linkify) |
| Type map built from source tree (not docs) | Ensures types are discovered even before their docs exist; the map reflects project structure |
| See Also always at end | Enforced during merge — prevents the section from being stranded mid-document after methods are appended |
| Re-linkify on every run | Even "up-to-date" files get a linkification pass, ensuring new types added to the project get linked retroactively |
| Relative source links | Documentation remains valid regardless of absolute project location |
| TODO placeholders | Templates are immediately identifiable as incomplete, guiding the author |
| Public methods first in TOC | Matches the convention used in existing project documentation |
| Single-pass field extraction (before first method) | Avoids capturing local variables inside method bodies as fields |
| Constructor detection via class name | Reliable heuristic that doesn't require full syntax analysis |
| SDD method detection via both headings and code blocks | Handles docs where methods are grouped under a single heading (e.g., "Getter Methods") |

---

## 11. Dependencies

| Dependency | Minimum Version | Reason |
|-----------|----------------|--------|
| Python | 3.7 | `dataclasses` module (introduced in 3.7); f-strings (3.6+); `typing` (3.5+) |

All imports are from the Python standard library — no `pip install` or `requirements.txt` needed.

| Module | Key Usage |
|--------|-----------|
| `os` | `os.walk`, `os.path.relpath`, `os.makedirs`, `os.path.exists` |
| `re` | `re.search`, `re.findall`, `re.sub`, `re.match` — Java parsing + inline linking |
| `sys` | `sys.exit(1)` on path validation failure |
| `argparse` | `ArgumentParser` for CLI with positional and optional args |
| `pathlib.Path` | Available but used sparingly; `os.path` is the primary path API |
| `dataclasses` | `@dataclass` for `MethodInfo`, `FieldInfo`, `JavaClassInfo` |
| `typing` | `List`, `Optional` for type annotations |

---

## 12. Known Limitations

- **Inner classes** — Not detected or documented separately; only the outermost class is parsed
- **Multi-line annotations** — Only single-line annotations immediately preceding a method are captured
- **Generic type parameters on class** — Not extracted (e.g., `class Foo<T>` captures `Foo` but not `<T>`)
- **Enum constants** — Not listed as fields for enum types
- **Interface default methods** — Parsed as regular methods (no special handling)
- **Overloaded methods** — Only one entry appears in the TOC (deduplicated by name), though all overloads get individual sections
- **External types** — Only project-internal types get linked; Bukkit/JDK types remain as plain backtick references
