"""
Documentation Template Generator for Java Plugin Projects.

Given a source code directory and documentation output folder,
this script generates template .md and _SDD.md documentation files mirroring
the source folder structure. Templates follow the existing documentation format.

Usage:
    python generate_docs.py <source_dir> <docs_output_dir>

Example:
    python generate_docs.py ../src/main/java/org/almond/buildinglore ../Documentation
"""

import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MethodInfo:
    name: str
    signature: str
    return_type: str
    parameters: List[tuple]  # [(type, name), ...]
    annotations: List[str] = field(default_factory=list)
    access: str = "public"
    is_static: bool = False
    is_constructor: bool = False


@dataclass
class FieldInfo:
    name: str
    type: str
    access: str = "private"
    is_static: bool = False
    is_final: bool = False


@dataclass
class JavaClassInfo:
    name: str
    file_name: str
    package: str
    imports: List[str]
    class_declaration: str
    fields: List[FieldInfo]
    methods: List[MethodInfo]
    extends_class: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    javadoc: Optional[str] = None


def parse_java_file(file_path: str) -> Optional[JavaClassInfo]:
    """Parse a Java file and extract class information."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    lines = content.split("\n")

    # Extract package
    package = ""
    pkg_match = re.search(r"^package\s+([\w.]+)\s*;", content, re.MULTILINE)
    if pkg_match:
        package = pkg_match.group(1)

    # Extract imports
    imports = re.findall(r"^import\s+([\w.*]+)\s*;", content, re.MULTILINE)

    # Extract class declaration
    class_match = re.search(
        r"(public\s+(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+"
        r"(\w+)(?:\s+extends\s+([\w<>,\s]+?))?(?:\s+implements\s+([\w<>,\s]+?))?\s*\{)",
        content,
    )

    if not class_match:
        return None

    class_declaration = class_match.group(1)
    class_name = class_match.group(2)
    extends_class = class_match.group(3).strip() if class_match.group(3) else None
    implements_raw = class_match.group(4)
    implements = (
        [i.strip() for i in implements_raw.split(",")]
        if implements_raw
        else []
    )

    # Extract class-level javadoc (immediately before class declaration)
    javadoc = None
    class_line_idx = content.find(class_match.group(0))
    before_class = content[:class_line_idx].rstrip()
    javadoc_match = re.search(r"/\*\*(.*?)\*/\s*$", before_class, re.DOTALL)
    if javadoc_match:
        raw = javadoc_match.group(1)
        javadoc = re.sub(r"^\s*\*\s?", "", raw, flags=re.MULTILINE).strip()

    # Extract fields
    fields = extract_fields(content, class_match.end())

    # Extract methods
    methods = extract_methods(content, class_name)

    file_name = os.path.basename(file_path)

    return JavaClassInfo(
        name=class_name,
        file_name=file_name,
        package=package,
        imports=imports,
        class_declaration=class_declaration,
        fields=fields,
        methods=methods,
        extends_class=extends_class,
        implements=implements,
        javadoc=javadoc,
    )


def extract_fields(content: str, class_body_start: int) -> List[FieldInfo]:
    """Extract field declarations from the class body."""
    fields = []
    # Match field declarations (not inside methods)
    # Look for lines like: private final Type name; or private Type name = ...;
    field_pattern = re.compile(
        r"^\s*((?:private|protected|public)\s+)?"
        r"(static\s+)?(final\s+)?"
        r"([\w<>\[\],\s]+?)\s+"
        r"(\w+)\s*(?:=|;)",
        re.MULTILINE,
    )

    # Only look at the top-level of the class (before first method)
    # Find the first method start
    method_start = re.search(
        r"(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:synchronized\s+)?"
        r"(?:[\w<>\[\],\s]+?)\s+\w+\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
        content[class_body_start:],
    )

    search_region = (
        content[class_body_start : class_body_start + method_start.start()]
        if method_start
        else content[class_body_start : class_body_start + 500]
    )

    for match in field_pattern.finditer(search_region):
        access = (match.group(1) or "package-private").strip()
        is_static = bool(match.group(2))
        is_final = bool(match.group(3))
        field_type = match.group(4).strip()
        field_name = match.group(5).strip()

        # Skip common false positives
        if field_type in ("return", "if", "for", "while", "new", "class", "import"):
            continue

        fields.append(
            FieldInfo(
                name=field_name,
                type=field_type,
                access=access,
                is_static=is_static,
                is_final=is_final,
            )
        )

    return fields


def extract_methods(content: str, class_name: str) -> List[MethodInfo]:
    """Extract method signatures from the class."""
    methods = []

    # Pattern for method declarations
    method_pattern = re.compile(
        r"(?:(@\w+(?:\([^)]*\))?)\s+)?"  # optional annotation
        r"(public|private|protected)\s+"
        r"(static\s+)?"
        r"(?:synchronized\s+)?"
        r"([\w<>\[\],?\s]+?)\s+"  # return type
        r"(\w+)\s*"  # method name
        r"\(([^)]*)\)\s*"  # parameters
        r"(?:throws\s+[\w,\s]+)?\s*\{",
        re.MULTILINE,
    )

    # Also match constructors
    constructor_pattern = re.compile(
        r"(?:(@\w+(?:\([^)]*\))?)\s+)?"
        r"(public|private|protected)\s+"
        + re.escape(class_name)
        + r"\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
        re.MULTILINE,
    )

    # Find constructors
    for match in constructor_pattern.finditer(content):
        annotation = match.group(1) or ""
        access = match.group(2)
        params_raw = match.group(3).strip()
        parameters = parse_parameters(params_raw)

        annotations = [annotation] if annotation else []
        sig = f"{access} {class_name}({params_raw})"

        methods.append(
            MethodInfo(
                name=class_name,
                signature=sig,
                return_type="",
                parameters=parameters,
                annotations=annotations,
                access=access,
                is_static=False,
                is_constructor=True,
            )
        )

    # Find methods
    for match in method_pattern.finditer(content):
        annotation = match.group(1) or ""
        access = match.group(2)
        is_static = bool(match.group(3))
        return_type = match.group(4).strip()
        method_name = match.group(5).strip()
        params_raw = match.group(6).strip()

        # Skip if this is actually a constructor (caught above)
        if method_name == class_name:
            continue

        parameters = parse_parameters(params_raw)
        annotations = [annotation] if annotation else []

        static_str = "static " if is_static else ""
        sig = f"{access} {static_str}{return_type} {method_name}({params_raw})"

        methods.append(
            MethodInfo(
                name=method_name,
                signature=sig,
                return_type=return_type,
                parameters=parameters,
                annotations=annotations,
                access=access,
                is_static=is_static,
                is_constructor=False,
            )
        )

    return methods


def parse_parameters(params_raw: str) -> List[tuple]:
    """Parse a parameter string into a list of (type, name) tuples."""
    if not params_raw:
        return []

    params = []
    for param in params_raw.split(","):
        param = param.strip()
        if not param:
            continue
        # Handle annotations in params (e.g., @NotNull String name)
        param = re.sub(r"@\w+\s+", "", param)
        parts = param.rsplit(" ", 1)
        if len(parts) == 2:
            params.append((parts[0].strip(), parts[1].strip()))
        else:
            params.append((param, ""))

    return params


def build_type_doc_map(source_dir: str, docs_output_dir: str) -> dict:
    """Build a mapping of class name -> relative doc path for all Java files in the source tree."""
    source_dir = os.path.abspath(source_dir)
    docs_output_dir = os.path.abspath(docs_output_dir)
    type_map = {}  # class_name -> absolute path of its .md doc file

    for root, dirs, files in os.walk(source_dir):
        java_files = [f for f in files if f.endswith(".java")]
        for java_file in java_files:
            class_name = java_file.replace(".java", "")
            rel_dir = os.path.relpath(root, source_dir)
            if rel_dir == ".":
                doc_path = os.path.join(docs_output_dir, f"{class_name}.md")
            else:
                doc_path = os.path.join(docs_output_dir, rel_dir, f"{class_name}.md")
            type_map[class_name] = os.path.abspath(doc_path)

    return type_map


def resolve_type_link(type_str: str, type_doc_map: dict, current_doc_dir: str, current_class: str = "") -> str:
    """Resolve a type string to a markdown link if documentation exists for it.
    
    Strips generics and array brackets to find the base type name.
    Returns the original type string wrapped in a link if found, otherwise returns it as-is in backticks.
    """
    # Extract the base type name (strip generics, arrays, wildcards)
    base_type = re.sub(r"<.*>", "", type_str)  # Remove generics
    base_type = re.sub(r"\[\]", "", base_type)  # Remove array brackets
    base_type = base_type.strip()

    # Don't link to self
    if base_type == current_class:
        return f"`{type_str}`"

    # Check if this type has documentation
    if base_type in type_doc_map:
        target_abs = type_doc_map[base_type]
        current_dir_abs = os.path.abspath(current_doc_dir)
        rel_path = os.path.relpath(target_abs, current_dir_abs).replace("\\", "/")
        return f"[`{type_str}`]({rel_path})"

    return f"`{type_str}`"


def linkify_inline_types(text: str, type_doc_map: dict, current_doc_dir: str, current_class: str = "") -> str:
    """Replace inline backtick-wrapped type references with links to their API docs.
    
    Matches `TypeName` in text (not already inside a markdown link) and replaces
    with [`TypeName`](path/to/TypeName.md) if documentation exists.
    """
    if not type_doc_map:
        return text

    def replace_backtick_ref(match):
        # Don't replace if already part of a link: [`Type`](...)
        # Check if preceded by [ 
        start = match.start()
        if start > 0 and text[start - 1] == "[":
            return match.group(0)

        type_name = match.group(1)
        # Extract base type (strip generics/arrays)
        base_type = re.sub(r"<.*>", "", type_name)
        base_type = re.sub(r"\[\]", "", base_type).strip()

        # Don't link to self
        if base_type == current_class:
            return match.group(0)

        # Check if this type has documentation
        if base_type in type_doc_map:
            target_abs = type_doc_map[base_type]
            current_dir_abs = os.path.abspath(current_doc_dir)
            rel_path = os.path.relpath(target_abs, current_dir_abs).replace("\\", "/")
            return f"[`{type_name}`]({rel_path})"

        return match.group(0)

    # Match `TypeName` but not already linked [`TypeName`](...)
    # Negative lookbehind for [ to avoid double-linking
    result = re.sub(r"(?<!\[)`([A-Z][\w<>\[\],\s]*?)`(?!\])", replace_backtick_ref, text)
    return result


def linkify_content(content: str, type_doc_map: dict, current_doc_dir: str, current_class: str = "") -> str:
    """Apply inline type linking to all lines in content, skipping code blocks."""
    lines = content.split("\n")
    result = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
        else:
            result.append(linkify_inline_types(line, type_doc_map, current_doc_dir, current_class))

    return "\n".join(result)


def compute_relative_source_path(
    source_file: str, source_root: str, doc_file_dir: str
) -> str:
    """Compute the relative path from the doc file to the source file."""
    source_abs = os.path.abspath(source_file)
    doc_dir_abs = os.path.abspath(doc_file_dir)

    return os.path.relpath(source_abs, doc_dir_abs).replace("\\", "/")


def build_api_header(class_info: JavaClassInfo, relative_source_path: str) -> List[str]:
    """Build the normalized header block for API docs."""
    sdd_filename = f"{class_info.name}_SDD.md"
    return [
        f"# {class_info.name}",
        "",
        f"> **Software Detailed Documentation:** [{sdd_filename}](./{sdd_filename})  ",
        f"> **Source File:** [{class_info.file_name}]({relative_source_path})",
        "",
    ]


def normalize_api_header(
    lines: List[str], class_info: JavaClassInfo, relative_source_path: str
) -> List[str]:
    """Replace the top title/header block in an API doc with the normalized format."""
    start = 0

    if lines and lines[0].startswith("# "):
        start = 1
        while start < len(lines) and not lines[start].strip():
            start += 1
        while start < len(lines) and lines[start].startswith("> "):
            start += 1
        while start < len(lines) and not lines[start].strip():
            start += 1

    return build_api_header(class_info, relative_source_path) + lines[start:]


# =============================================================================
# Merge Logic — update existing docs without losing manual content
# =============================================================================


def parse_existing_api_doc(file_path: str) -> dict:
    """Parse an existing API .md file and extract documented method names and structure.
    
    Returns a dict with:
      - 'content': full file content
      - 'documented_methods': set of method names found as ## headings
      - 'documented_fields': set of field names found in the Fields section
      - 'toc_end_line': line index where the Functions TOC ends
      - 'methods_start_line': line index where method sections begin (first ---)
      - 'see_also_line': line index of the See Also section (or -1)
      - 'lines': list of all lines
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    documented_methods = set()
    documented_fields = set()
    toc_end_line = -1
    methods_start_line = -1
    see_also_line = -1
    in_fields = False
    in_toc = False

    for i, line in enumerate(lines):
        # Detect fields section
        if line.startswith("**Fields:**"):
            in_fields = True
            continue
        if in_fields:
            field_match = re.match(r"^- `(\w+)`", line)
            if field_match:
                documented_fields.add(field_match.group(1))
            elif not line.strip():
                in_fields = False

        # Detect Functions TOC
        if line.startswith("**Functions:**"):
            in_toc = True
            continue
        if in_toc:
            if line.startswith("- ["):
                continue
            elif not line.strip():
                toc_end_line = i
                in_toc = False

        # Detect method sections (## headings)
        heading_match = re.match(r"^## (.+?)(?:\s*\(Constructor\))?\s*$", line)
        if heading_match:
            method_name = heading_match.group(1).strip()
            documented_methods.add(method_name)
            if methods_start_line == -1:
                # The --- before the first method section
                for j in range(i - 1, -1, -1):
                    if lines[j].strip() == "---":
                        methods_start_line = j
                        break
                if methods_start_line == -1:
                    methods_start_line = i

        # Detect See Also section
        if line.strip() == "## See Also":
            see_also_line = i
            # Also include the --- before it
            for j in range(i - 1, -1, -1):
                if lines[j].strip() == "---":
                    see_also_line = j
                    break

    return {
        "content": content,
        "documented_methods": documented_methods,
        "documented_fields": documented_fields,
        "toc_end_line": toc_end_line,
        "methods_start_line": methods_start_line,
        "see_also_line": see_also_line,
        "lines": lines,
    }


def parse_existing_sdd_doc(file_path: str) -> dict:
    """Parse an existing SDD _SDD.md file and extract documented method section names.
    
    Detects methods by:
      1. Numbered section headings like: ## 5. `methodName()`
      2. Method signatures in code blocks (handles methods grouped in a single section)
    
    Returns a dict with:
      - 'content': full file content
      - 'documented_methods': set of method names found
      - 'last_section_num': the highest section number found
      - 'lines': list of all lines
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    documented_methods = set()
    last_section_num = 0

    for line in lines:
        # Match sections like: ## 5. `methodName()`  or  ## 5. Constructor
        section_match = re.match(r"^## (\d+)\.\s+(?:`(\w+)\(\)`|Constructor)\s*$", line)
        if section_match:
            num = int(section_match.group(1))
            last_section_num = max(last_section_num, num)
            if section_match.group(2):
                documented_methods.add(section_match.group(2))
            else:
                documented_methods.add("__constructor__")
            continue

        # Match any numbered section heading (e.g., ## 7. Getter Methods)
        any_section_match = re.match(r"^## (\d+)\.", line)
        if any_section_match:
            num = int(any_section_match.group(1))
            last_section_num = max(last_section_num, num)

        # Also detect method signatures in code blocks to catch grouped methods
        # Matches: public ReturnType methodName(  or  private void methodName(
        sig_match = re.match(
            r"^(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\],?\s]+?)\s+(\w+)\s*\(",
            line.strip(),
        )
        if sig_match:
            documented_methods.add(sig_match.group(1))

    return {
        "content": content,
        "documented_methods": documented_methods,
        "last_section_num": last_section_num,
        "lines": lines,
    }


def generate_api_method_section(method: MethodInfo, type_doc_map: dict, doc_dir: str, class_name: str) -> str:
    """Generate a single method section for the API doc."""
    lines = []

    if method.is_constructor:
        lines.append(f"## {method.name} (Constructor)")
    else:
        lines.append(f"## {method.name}")
    lines.append("")

    lines.append("### Signature")
    lines.append("```java")
    if method.annotations:
        for ann in method.annotations:
            lines.append(ann)
    lines.append(method.signature)
    lines.append("```")
    lines.append("")

    lines.append("### Description")
    lines.append(f"TODO: Describe what `{method.name}` does.")
    lines.append("")

    if method.parameters:
        lines.append("### Parameters")
        lines.append("| Name | Type | Description |")
        lines.append("|------|------|-------------|")
        for ptype, pname in method.parameters:
            type_link = resolve_type_link(ptype, type_doc_map, doc_dir, class_name)
            lines.append(f"| `{pname}` | {type_link} | TODO: describe |")
        lines.append("")
    else:
        lines.append("### Parameters")
        lines.append("None.")
        lines.append("")

    lines.append("### Returns")
    if method.is_constructor:
        lines.append(f"`{method.name}` instance.")
    elif method.return_type == "void":
        lines.append("`void`")
    else:
        ret_link = resolve_type_link(method.return_type, type_doc_map, doc_dir, class_name)
        lines.append(f"{ret_link} — TODO: describe return value.")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def generate_sdd_method_section(method: MethodInfo, section_num: int) -> str:
    """Generate a single method section for the SDD doc."""
    lines = []

    if method.is_constructor:
        lines.append(f"## {section_num}. Constructor")
    else:
        lines.append(f"## {section_num}. `{method.name}()`")
    lines.append("")

    lines.append("```java")
    if method.annotations:
        for ann in method.annotations:
            lines.append(ann)
    lines.append(method.signature)
    lines.append("```")
    lines.append("")
    lines.append(f"TODO: Provide detailed design explanation for `{method.name}`.")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def merge_api_doc(
    existing_path: str,
    class_info: JavaClassInfo,
    type_doc_map: dict,
    doc_dir: str,
    relative_source_path: str,
) -> str:
    """Merge new methods/fields into an existing API doc without removing existing content."""
    parsed = parse_existing_api_doc(existing_path)
    original_lines = parsed["lines"]
    lines = normalize_api_header(original_lines, class_info, relative_source_path)

    new_fields = []
    new_methods = []
    new_toc_entries = []

    # Find fields that are in source but not in the doc
    for f in class_info.fields:
        if f.name not in parsed["documented_fields"]:
            type_link = resolve_type_link(f.type, type_doc_map, doc_dir, class_info.name)
            new_fields.append(f"- `{f.name}` ({type_link}) — TODO: describe field")

    # Collect existing TOC entries to avoid duplicates
    existing_toc_names = set()
    for line in lines:
        toc_match = re.match(r"^- \[(.+?)\]\(#", line)
        if toc_match:
            existing_toc_names.add(toc_match.group(1).lower())

    # Find methods that are in source but not in the doc
    for method in class_info.methods:
        method_doc_name = method.name
        if method_doc_name not in parsed["documented_methods"]:
            new_methods.append(method)
            display_name = method.name if not method.is_constructor else f"{method.name} (Constructor)"
            anchor = method.name.lower().replace(" ", "-")
            # Only add TOC entry if not already present
            if display_name.lower() not in existing_toc_names:
                new_toc_entries.append(f"- [{display_name}](#{anchor})")

    header_changed = lines != original_lines

    if not new_fields and not new_methods:
        # Still check if See Also section needs to be moved to end
        see_also_found = False
        see_also_at_end = True
        for i, line in enumerate(lines):
            if re.match(r"^##\s+See Also", line):
                see_also_found = True
                # Check if there are any ## headings after this
                for j in range(i + 1, len(lines)):
                    if re.match(r"^## ", lines[j]) and not re.match(r"^##\s+See Also", lines[j]):
                        see_also_at_end = False
                        break
                break
        if see_also_found and not see_also_at_end:
            pass  # Fall through to the repositioning logic below
        else:
            return "\n".join(lines) if header_changed else None

    # Insert new fields into the fields section
    if new_fields:
        # Find the end of the fields list (blank line after last field entry)
        fields_end = -1
        in_fields = False
        for i, line in enumerate(lines):
            if line.startswith("**Fields:**"):
                in_fields = True
                continue
            if in_fields:
                if re.match(r"^- `\w+`", line):
                    fields_end = i
                elif not line.strip():
                    break
        if fields_end >= 0:
            # Insert after the last field line
            for j, new_field in enumerate(new_fields):
                lines.insert(fields_end + 1 + j, new_field)

    # Insert new TOC entries
    if new_toc_entries and parsed["toc_end_line"] >= 0:
        # Recalculate toc_end_line after potential field insertions
        toc_end = -1
        in_toc = False
        for i, line in enumerate(lines):
            if line.startswith("**Functions:**"):
                in_toc = True
                continue
            if in_toc:
                if line.startswith("- ["):
                    toc_end = i
                elif not line.strip():
                    break
        if toc_end >= 0:
            for j, entry in enumerate(new_toc_entries):
                lines.insert(toc_end + 1 + j, entry)

    # Insert new method sections before the See Also section (or at end)
    if new_methods:
        # Find and remove the See Also section so we can re-append it at the very end
        see_also_start = -1
        see_also_lines = []
        for i, line in enumerate(lines):
            if re.match(r"^##\s+See Also", line):
                # Find the start (include preceding --- if present)
                see_also_start = i
                for j in range(i - 1, -1, -1):
                    if lines[j].strip() == "---":
                        see_also_start = j
                        break
                    elif lines[j].strip():
                        break
                see_also_lines = lines[see_also_start:]
                lines = lines[:see_also_start]
                break

        # Remove trailing blank lines and separators before appending See Also
        while lines and not lines[-1].strip():
            lines.pop()
        # Remove trailing --- to avoid stacking separators
        while lines and lines[-1].strip() == "---":
            lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append("")

        # Append new method sections
        for method in new_methods:
            section = generate_api_method_section(method, type_doc_map, doc_dir, class_info.name)
            lines.extend(section.split("\n"))

        # Re-append See Also at the very end
        # Remove trailing blank/separator lines before See Also
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and lines[-1].strip() == "---":
            lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()

        if see_also_lines:
            # Remove leading blank lines and separators from see_also
            while see_also_lines and not see_also_lines[0].strip():
                see_also_lines.pop(0)
            while see_also_lines and see_also_lines[0].strip() == "---":
                see_also_lines.pop(0)
            while see_also_lines and not see_also_lines[0].strip():
                see_also_lines.pop(0)
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.extend(see_also_lines)
        else:
            # Add a new See Also section if one didn't exist
            sdd_filename = f"{class_info.name}_SDD.md"
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## See Also")
            lines.append("")
            lines.append(f"- **Software Detailed Design:** [{sdd_filename}](./{sdd_filename})")
            lines.append("")
    else:
        # Even if no new methods, ensure See Also is at end if it was misplaced
        see_also_start = -1
        see_also_lines = []
        for i, line in enumerate(lines):
            if re.match(r"^##\s+See Also", line):
                see_also_start = i
                for j in range(i - 1, -1, -1):
                    if lines[j].strip() == "---":
                        see_also_start = j
                        break
                    elif lines[j].strip():
                        break
                see_also_lines = lines[see_also_start:]
                lines = lines[:see_also_start]
                break

        if see_also_lines:
            # Re-append at end with clean separators
            while lines and not lines[-1].strip():
                lines.pop()
            while lines and lines[-1].strip() == "---":
                lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
            # Clean up see_also_lines
            while see_also_lines and not see_also_lines[0].strip():
                see_also_lines.pop(0)
            while see_also_lines and see_also_lines[0].strip() == "---":
                see_also_lines.pop(0)
            while see_also_lines and not see_also_lines[0].strip():
                see_also_lines.pop(0)
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.extend(see_also_lines)

    return "\n".join(lines)


def merge_sdd_doc(existing_path: str, class_info: JavaClassInfo) -> str:
    """Merge new method sections into an existing SDD doc without removing existing content."""
    parsed = parse_existing_sdd_doc(existing_path)
    lines = parsed["lines"]

    new_methods = []
    for method in class_info.methods:
        lookup_name = "__constructor__" if method.is_constructor else method.name
        if lookup_name not in parsed["documented_methods"]:
            new_methods.append(method)

    if not new_methods:
        return None  # Nothing to merge

    # Append new sections at the end of the file
    next_section_num = parsed["last_section_num"] + 1
    new_sections = []
    for method in new_methods:
        section = generate_sdd_method_section(method, next_section_num)
        new_sections.append(section)
        next_section_num += 1

    # Remove trailing blank lines and append
    while lines and not lines[-1].strip():
        lines.pop()

    lines.append("")
    for section in new_sections:
        lines.extend(section.split("\n"))

    return "\n".join(lines)


def generate_api_doc(
    class_info: JavaClassInfo, relative_source_path: str,
    type_doc_map: dict = None, doc_dir: str = ""
) -> str:
    """Generate the API documentation (.md) template."""
    if type_doc_map is None:
        type_doc_map = {}
    lines = build_api_header(class_info, relative_source_path)

    # Description placeholder
    if class_info.javadoc:
        lines.append(class_info.javadoc)
    else:
        lines.append(f"TODO: Add description for `{class_info.name}`.")
    lines.append("")

    # Fields section
    if class_info.fields:
        lines.append("---")
        lines.append("")
        lines.append("## Table of Contents")
        lines.append("")
        lines.append("**Fields:**")
        for f in class_info.fields:
            type_link = resolve_type_link(f.type, type_doc_map, doc_dir, class_info.name)
            lines.append(f"- `{f.name}` ({type_link}) — TODO: describe field")
        lines.append("")

    # Constants section
    constants = [f for f in class_info.fields if f.is_static and f.is_final]
    non_constant_fields = [
        f for f in class_info.fields if not (f.is_static and f.is_final)
    ]
    if constants and non_constant_fields:
        # Already listed all above, no need to separate
        pass

    # Functions table of contents
    if class_info.methods:
        public_methods = [m for m in class_info.methods if m.access == "public"]
        private_methods = [m for m in class_info.methods if m.access != "public"]
        
        all_display_methods = public_methods + private_methods
        if all_display_methods:
            if not class_info.fields:
                lines.append("---")
                lines.append("")
                lines.append("## Table of Contents")
                lines.append("")
            lines.append("**Functions:**")
            seen_names = set()
            for m in all_display_methods:
                display_name = m.name if not m.is_constructor else f"{m.name} (Constructor)"
                anchor = m.name.lower().replace(" ", "-")
                if m.name not in seen_names:
                    lines.append(f"- [{display_name}](#{anchor})")
                    seen_names.add(m.name)
            lines.append("")

    # Method details
    lines.append("---")
    lines.append("")

    for method in class_info.methods:
        if method.is_constructor:
            lines.append(f"## {method.name} (Constructor)")
        else:
            lines.append(f"## {method.name}")
        lines.append("")

        lines.append("### Signature")
        lines.append("```java")
        if method.annotations:
            for ann in method.annotations:
                lines.append(ann)
        lines.append(method.signature)
        lines.append("```")
        lines.append("")

        lines.append("### Description")
        lines.append(f"TODO: Describe what `{method.name}` does.")
        lines.append("")

        if method.parameters:
            lines.append("### Parameters")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for ptype, pname in method.parameters:
                type_link = resolve_type_link(ptype, type_doc_map, doc_dir, class_info.name)
                lines.append(f"| `{pname}` | {type_link} | TODO: describe |")
            lines.append("")
        else:
            lines.append("### Parameters")
            lines.append("None.")
            lines.append("")

        lines.append("### Returns")
        if method.is_constructor:
            lines.append(f"`{method.name}` instance.")
        elif method.return_type == "void":
            lines.append("`void`")
        else:
            ret_link = resolve_type_link(method.return_type, type_doc_map, doc_dir, class_info.name)
            lines.append(f"{ret_link} — TODO: describe return value.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # See Also section
    sdd_filename = f"{class_info.name}_SDD.md"
    lines.append("## See Also")
    lines.append("")
    lines.append(f"- **Software Detailed Design:** [{sdd_filename}](./{sdd_filename})")
    lines.append("")

    content = "\n".join(lines)
    return linkify_content(content, type_doc_map, doc_dir, class_info.name)


def generate_sdd_doc(
    class_info: JavaClassInfo,
    relative_source_path: str,
    api_doc_filename: str,
    type_doc_map: dict = None,
    doc_dir: str = "",
) -> str:
    """Generate the Software Detailed Design (_SDD.md) template."""
    if type_doc_map is None:
        type_doc_map = {}
    lines = []

    # Title
    lines.append(f"# {class_info.name} — Software Detailed Design")
    lines.append("")

    # Header links
    lines.append(f"> **API Documentation:** [{api_doc_filename}](./{api_doc_filename})  ")
    lines.append(
        f"> **Source File:** [{class_info.file_name}]({relative_source_path})"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 1: Overview
    lines.append("## 1. Overview")
    lines.append("")
    if class_info.javadoc:
        lines.append(class_info.javadoc)
    else:
        lines.append(f"TODO: Provide a high-level overview of `{class_info.name}`.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 2: Package & Imports
    lines.append("## 2. Package Declaration & Imports")
    lines.append("")
    lines.append("```java")
    lines.append(f"package {class_info.package};")
    lines.append("```")
    lines.append("")

    if class_info.imports:
        lines.append("```java")
        for imp in class_info.imports:
            lines.append(f"import {imp};")
        lines.append("```")
        lines.append("")

        lines.append("| Import | Purpose |")
        lines.append("|--------|---------|")
        for imp in class_info.imports:
            short_name = imp.split(".")[-1]
            lines.append(f"| `{short_name}` | TODO: describe purpose |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Section 3: Class Declaration
    lines.append("## 3. Class Declaration")
    lines.append("")
    lines.append("```java")
    lines.append(class_info.class_declaration)
    lines.append("```")
    lines.append("")

    if class_info.extends_class:
        lines.append(
            f"- **`extends {class_info.extends_class}`** — TODO: explain inheritance."
        )
    if class_info.implements:
        lines.append(
            f"- **`implements {', '.join(class_info.implements)}`** — TODO: explain interfaces."
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 4: Instance Fields
    section_num = 4
    if class_info.fields:
        lines.append(f"## {section_num}. Instance Fields")
        lines.append("")
        lines.append("```java")
        for f in class_info.fields:
            static_str = "static " if f.is_static else ""
            final_str = "final " if f.is_final else ""
            lines.append(f"{f.access} {static_str}{final_str}{f.type} {f.name};")
        lines.append("```")
        lines.append("")

        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for f in class_info.fields:
            lines.append(f"| `{f.name}` | `{f.type}` | TODO: describe |")
        lines.append("")
        lines.append("---")
        lines.append("")
        section_num += 1

    # Method sections
    for method in class_info.methods:
        if method.is_constructor:
            lines.append(f"## {section_num}. Constructor")
        else:
            lines.append(f"## {section_num}. `{method.name}()`")
        lines.append("")

        lines.append("```java")
        if method.annotations:
            for ann in method.annotations:
                lines.append(ann)
        lines.append(method.signature)
        lines.append("```")
        lines.append("")
        lines.append(f"TODO: Provide detailed design explanation for `{method.name}`.")
        lines.append("")
        lines.append("---")
        lines.append("")
        section_num += 1

    content = "\n".join(lines)
    return linkify_content(content, type_doc_map, doc_dir, class_info.name)


def process_source_directory(
    source_dir: str, docs_output_dir: str, overwrite: bool = False
):
    """Walk the source directory and generate documentation templates."""
    source_dir = os.path.abspath(source_dir)
    docs_output_dir = os.path.abspath(docs_output_dir)

    # Build type-to-doc-path mapping for cross-referencing
    type_doc_map = build_type_doc_map(source_dir, docs_output_dir)

    # Determine the base package directory structure
    # We want to mirror subfolders relative to source_dir
    generated_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(source_dir):
        java_files = [f for f in files if f.endswith(".java")]
        if not java_files:
            continue

        # Compute relative path from source root
        rel_dir = os.path.relpath(root, source_dir)
        if rel_dir == ".":
            # Files at the root of source_dir go directly into docs_output_dir
            doc_dir = docs_output_dir
        else:
            doc_dir = os.path.join(docs_output_dir, rel_dir)

        # Create output directory
        os.makedirs(doc_dir, exist_ok=True)

        for java_file in java_files:
            source_file = os.path.join(root, java_file)
            base_name = java_file.replace(".java", "")
            api_doc_path = os.path.join(doc_dir, f"{base_name}.md")
            sdd_doc_path = os.path.join(doc_dir, f"{base_name}_SDD.md")

            # Parse the Java file
            class_info = parse_java_file(source_file)
            if not class_info:
                print(f"  WARN: Could not parse {java_file}")
                continue

            # Compute relative path from doc file to source file
            relative_source = compute_relative_source_path(
                source_file, source_dir, doc_dir
            )

            api_exists = os.path.exists(api_doc_path)
            sdd_exists = os.path.exists(sdd_doc_path)

            if overwrite:
                # Full regeneration
                api_content = generate_api_doc(class_info, relative_source, type_doc_map, doc_dir)
                with open(api_doc_path, "w", encoding="utf-8") as f:
                    f.write(api_content)
                print(f"  CREATED: {os.path.relpath(api_doc_path, docs_output_dir)}")

                sdd_content = generate_sdd_doc(
                    class_info, relative_source, f"{base_name}.md", type_doc_map, doc_dir
                )
                with open(sdd_doc_path, "w", encoding="utf-8") as f:
                    f.write(sdd_content)
                print(f"  CREATED: {os.path.relpath(sdd_doc_path, docs_output_dir)}")
                generated_count += 1

            elif api_exists and sdd_exists:
                # Merge mode — add missing sections without removing existing content
                merged_api = merge_api_doc(
                    api_doc_path,
                    class_info,
                    type_doc_map,
                    doc_dir,
                    relative_source,
                )
                merged_sdd = merge_sdd_doc(sdd_doc_path, class_info)

                if merged_api:
                    merged_api = linkify_content(merged_api, type_doc_map, doc_dir, class_info.name)
                    with open(api_doc_path, "w", encoding="utf-8") as f:
                        f.write(merged_api)
                    print(f"  MERGED:  {os.path.relpath(api_doc_path, docs_output_dir)}")
                else:
                    # Still re-linkify even if no new sections
                    with open(api_doc_path, "r", encoding="utf-8") as f:
                        api_text = f.read()
                    linked_api = linkify_content(api_text, type_doc_map, doc_dir, class_info.name)
                    if linked_api != api_text:
                        with open(api_doc_path, "w", encoding="utf-8") as f:
                            f.write(linked_api)

                if merged_sdd:
                    merged_sdd = linkify_content(merged_sdd, type_doc_map, doc_dir, class_info.name)
                    with open(sdd_doc_path, "w", encoding="utf-8") as f:
                        f.write(merged_sdd)
                    print(f"  MERGED:  {os.path.relpath(sdd_doc_path, docs_output_dir)}")
                else:
                    # Still re-linkify even if no new sections
                    with open(sdd_doc_path, "r", encoding="utf-8") as f:
                        sdd_text = f.read()
                    linked_sdd = linkify_content(sdd_text, type_doc_map, doc_dir, class_info.name)
                    if linked_sdd != sdd_text:
                        with open(sdd_doc_path, "w", encoding="utf-8") as f:
                            f.write(linked_sdd)

                if not merged_api and not merged_sdd:
                    print(f"  UP-TO-DATE: {base_name}.md & {base_name}_SDD.md")
                    skipped_count += 1
                else:
                    generated_count += 1

            else:
                # Create new files
                if not api_exists:
                    api_content = generate_api_doc(class_info, relative_source, type_doc_map, doc_dir)
                    with open(api_doc_path, "w", encoding="utf-8") as f:
                        f.write(api_content)
                    print(f"  CREATED: {os.path.relpath(api_doc_path, docs_output_dir)}")

                if not sdd_exists:
                    sdd_content = generate_sdd_doc(
                        class_info, relative_source, f"{base_name}.md", type_doc_map, doc_dir
                    )
                    with open(sdd_doc_path, "w", encoding="utf-8") as f:
                        f.write(sdd_content)
                    print(f"  CREATED: {os.path.relpath(sdd_doc_path, docs_output_dir)}")

                generated_count += 1

    return generated_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation templates from Java source files."
    )
    parser.add_argument(
        "source_dir",
        help="Path to the Java source code root directory (e.g., src/main/java/org/almond/buildinglore)",
    )
    parser.add_argument(
        "docs_output_dir",
        help="Path to the documentation output directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing documentation files (default: skip existing)",
    )

    args = parser.parse_args()

    # Validate paths
    if not os.path.isdir(args.source_dir):
        print(f"ERROR: Source directory not found: {args.source_dir}")
        sys.exit(1)

    print(f"Source directory: {os.path.abspath(args.source_dir)}")
    print(f"Output directory: {os.path.abspath(args.docs_output_dir)}")
    print(f"Overwrite mode:  {'ON' if args.overwrite else 'OFF'}")
    print()
    print("Generating documentation templates...")
    print("-" * 50)

    generated, skipped = process_source_directory(
        args.source_dir, args.docs_output_dir, args.overwrite
    )

    print("-" * 50)
    print(f"Done. Generated: {generated} file pairs, Skipped: {skipped} (already exist)")


if __name__ == "__main__":
    main()
