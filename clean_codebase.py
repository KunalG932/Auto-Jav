#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path
from typing import List, Set

EXCLUDED_DIRS: Set[str] = {
    '__pycache__', '.git', '.venv', 'venv', 'env', 
    'node_modules', '.pytest_cache', '.mypy_cache',
    'downloads', '.azure'
}

EXCLUDED_FILES: Set[str] = {
    'clean_codebase.py', '__init__.py'
}

MD_FILES_TO_KEEP: Set[str] = {
    'README.md', 'LICENSE'
}

def should_process_file(filepath: Path) -> bool:
    if filepath.name in EXCLUDED_FILES:
        return False
    for excluded_dir in EXCLUDED_DIRS:
        if excluded_dir in filepath.parts:
            return False
    return True

def remove_python_comments(content: str) -> str:
    lines = content.split('\n')
    cleaned_lines = []
    in_docstring = False
    docstring_char = None
    
    for line in lines:
        stripped = line.lstrip()
        
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    continue
                else:
                    in_docstring = True
                    continue
            
            if stripped.startswith('#'):
                continue
            
            if '#' in line:
                code_part = line.split('#')[0].rstrip()
                if code_part:
                    cleaned_lines.append(code_part)
            else:
                cleaned_lines.append(line)
        else:
            if docstring_char and docstring_char in stripped:
                in_docstring = False
                docstring_char = None
            continue
    
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result

def clean_python_file(filepath: Path) -> bool:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        cleaned_content = remove_python_comments(original_content)
        
        if cleaned_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def should_delete_md_file(filepath: Path) -> bool:
    return filepath.name not in MD_FILES_TO_KEEP

def clean_md_files(root_dir: Path) -> tuple[int, int]:
    deleted_count = 0
    kept_count = 0
    
    for filepath in root_dir.rglob('*.md'):
        if not should_process_file(filepath):
            continue
        
        if should_delete_md_file(filepath):
            try:
                filepath.unlink()
                print(f"Deleted: {filepath.relative_to(root_dir)}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {filepath}: {e}")
        else:
            print(f"Kept: {filepath.relative_to(root_dir)}")
            kept_count += 1
    
    return deleted_count, kept_count

def clean_python_files(root_dir: Path) -> int:
    modified_count = 0
    
    for filepath in root_dir.rglob('*.py'):
        if not should_process_file(filepath):
            continue
        
        if clean_python_file(filepath):
            print(f"Cleaned: {filepath.relative_to(root_dir)}")
            modified_count += 1
    
    return modified_count

def main():
    root_dir = Path(__file__).parent.resolve()
    
    print("=" * 60)
    print("CODEBASE CLEANER")
    print("=" * 60)
    print(f"Root directory: {root_dir}")
    print()
    
    print("Phase 1: Removing comments from Python files...")
    print("-" * 60)
    py_modified = clean_python_files(root_dir)
    print(f"\nPython files cleaned: {py_modified}")
    print()
    
    print("Phase 2: Cleaning markdown files...")
    print("-" * 60)
    md_deleted, md_kept = clean_md_files(root_dir)
    print(f"\nMarkdown files deleted: {md_deleted}")
    print(f"Markdown files kept: {md_kept}")
    print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Python files modified: {py_modified}")
    print(f"Markdown files deleted: {md_deleted}")
    print(f"Markdown files kept: {md_kept}")
    print()
    print("Codebase cleaning complete!")

if __name__ == "__main__":
    main()
