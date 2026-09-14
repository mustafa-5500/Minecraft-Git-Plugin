# generate_docs.py

> **Software Detailed Documentation:** [generate_docs_SDD.md](./generate_docs_SDD.md)  
> **Source File:** [generate_docs.py](./generate_docs.py)

A Python script that automatically generates template documentation files from Java source code. It parses `.java` files and produces both API reference (`.md`) and Software Detailed Design (`_SDD.md`) templates mirroring the source folder structure.

---

## Table of Contents

- [Usage](#usage)
- [Output](#output)
- [Behavior](#behavior)
- [Console Output](#console-output)
- [Dependencies](#dependencies)

---

## Usage

```
python generate_docs.py <source_dir> <docs_output_dir> [--overwrite]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `source_dir` | Yes | Path to the Java source code root directory (e.g., `src/main/java/org/almond/buildinglore`) |
| `docs_output_dir` | Yes | Path to the documentation output directory (e.g., `Documentation`) |
| `--overwrite` | No | If set, regenerates all documentation files from scratch. Default behavior merges new content into existing files. |

### Examples

Generate/merge docs (default):
```
python Utils/documentation-generator/generate_docs.py src/main/java/org/almond/buildinglore Documentation
```

Regenerate all docs (overwrite):
```
python Utils/documentation-generator/generate_docs.py src/main/java/org/almond/buildinglore Documentation --overwrite
```

---

## Output

The script produces two files per Java source file:

### `[ClassName].md` — API Documentation

Contains:
- **Title** — Plain class name heading (for example, `# WandUtil`)
- **Header** — Top links to the corresponding SDD doc and source file
- **Description** — Extracted from class-level Javadoc, or a `TODO` placeholder
- **Table of Contents** — Dedicated section containing fields and function links
- **Fields** — List of class fields with type links to corresponding API docs
- **Functions** — In-page links to each method section
- **Method Sections** — For each method:
  - Signature (with annotations)
  - Description placeholder
  - Parameter table (type linked, name, description)
  - Return type (linked to API doc if applicable)
- **See Also** — Link to the corresponding SDD document

### `[ClassName]_SDD.md` — Software Detailed Design

Contains:
- **Header** — Links to the API doc and source file
- **Section 1: Overview** — High-level description from Javadoc or placeholder
- **Section 2: Package Declaration & Imports** — Full import list with purpose table
- **Section 3: Class Declaration** — Class signature with inheritance/interface notes
- **Section 4: Instance Fields** — Code block and description table
- **Sections 5+: Methods** — One section per method with signature and design placeholder

### Folder Structure

The output mirrors the source directory hierarchy:

```
source_dir/                    docs_output_dir/
├── BuildingLorePlugin.java    ├── BuildingLorePlugin.md
│                              ├── BuildingLorePlugin_SDD.md
├── command/                   ├── command/
│   └── MyCommand.java         │   ├── MyCommand.md
│                              │   └── MyCommand_SDD.md
├── model/                     ├── model/
│   └── MyModel.java           │   ├── MyModel.md
│                              │   └── MyModel_SDD.md
```

---

## Behavior

### Merge Mode (Default)

When both `.md` and `_SDD.md` already exist for a source file, the script operates in **merge mode**:

- **New methods** — Methods found in source but not in the doc are appended as new sections (both API and SDD).
- **New fields** — Fields found in source but not in the doc are added to the Fields list.
- **TOC updated** — New method entries are added to the Functions table of contents.
- **API header normalized** — Existing API docs have their top title/header block rewritten to the current format (`# ClassName`, `Software Detailed Documentation`, `Source File`).
- **Existing content preserved** — Manually-written descriptions, design notes, and other content are never overwritten or removed.
- **See Also enforcement** — The See Also section is always repositioned to the end of the API doc.
- **Deduplication** — Methods already documented (by heading name or code block signature) are not re-added.

### Inline Type Linking

All output (generated, merged, or re-linkified) passes through the **inline type linking** system:

- Scans all non-code-block lines for backtick-wrapped type names (e.g., `` `SelectionManager` ``)
- If a matching API documentation file exists, wraps the reference as a markdown link: `` [`SelectionManager`](manager/SelectionManager.md) ``
- Skips types that are already linked (`` [`Type`](...) ``)
- Skips references to the current class (no self-links)
- Handles generics and array brackets (e.g., `` `List<Selection>` `` links via the base type)

### Overwrite Mode (`--overwrite`)

Regenerates all documentation files from scratch. **All existing content is replaced** — use with caution.

### Other Behavior

- **Relative links** — Source file links and type cross-references use relative paths computed from the doc file location.
- **TODO placeholders** — All descriptions are filled with `TODO:` markers for manual completion.
- **Javadoc extraction** — If a class has a Javadoc comment immediately above the class declaration, it is used as the description instead of a TODO placeholder.
- **Constructor detection** — Constructors are identified and labeled separately from regular methods.
- **Annotation preservation** — Method annotations (e.g., `@Override`) are included in the signature block.
- **Type cross-referencing** — Parameter types and return types in structured positions are linked to their API docs when available.

---

## Console Output

```
Source directory: C:\...\src\main\java\org\almond\buildinglore
Output directory: C:\...\Documentation
Overwrite mode:  OFF

Generating documentation templates...
--------------------------------------------------
  CREATED: BuildingLorePlugin.md
  CREATED: BuildingLorePlugin_SDD.md
  MERGED:  command\BuildingLoreCommand.md
  MERGED:  command\BuildingLoreCommand_SDD.md
  UP-TO-DATE: Selection.md & Selection_SDD.md
  WARN: Could not parse InvalidFile.java
--------------------------------------------------
Done. Generated: 2 file pairs, Skipped: 1 (already exist)
```

| Status | Meaning |
|--------|---------|
| `CREATED` | New documentation file generated from scratch |
| `MERGED` | Existing file updated with new methods/fields (existing content preserved) |
| `UP-TO-DATE` | No changes needed — source and docs are in sync |
| `WARN` | Java file could not be parsed (skipped) |

---

## Dependencies

| Dependency | Version | Notes |
|-----------|---------|-------|
| Python | 3.7+ | Uses `dataclasses` (3.7+), `typing` (3.5+), `pathlib` (3.4+) |

### Standard Library Modules Used

| Module | Purpose |
|--------|---------|
| `os` | File system operations, path resolution, directory walking |
| `re` | Regular expressions for Java source parsing and inline type detection |
| `sys` | Process exit on validation errors |
| `argparse` | CLI argument parsing and help generation |
| `pathlib.Path` | Object-oriented path manipulation |
| `dataclasses` | Declarative data classes (`@dataclass`, `field`) |
| `typing` | Type annotations (`List`, `Optional`) |

No external/third-party packages are required.
