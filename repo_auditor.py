import os
import re
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RepoAuditor")

class RepositoryAuditor:
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.excluded_dirs = {".git", "__pycache__", "venv", ".pytest_cache"}

    def audit_and_fix(self):
        """Walks through the repository, auditing and improving Python files."""
        logger.info(f"Starting repository audit across: {os.path.abspath(self.root_dir)}")
        
        modified_files_count = 0
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in self.excluded_dirs]
            
            for file in filenames:
                if file.endswith(".py") and file != "repo_auditor.py":
                    file_path = os.path.join(dirpath, file)
                    if self._process_file(file_path):
                        modified_files_count += 1

        logger.info(f"Audit complete. Total files improved/fixed: {modified_files_count}")

    def _process_file(self, file_path: str) -> bool:
        """Reads a file, applies fixes, and saves if changes were made."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            updated_content = content
            
            # 1. Apply code improvements & fixes
            updated_content = self._fix_deprecated_replacements(updated_content)
            updated_content = self._ensure_future_imports(updated_content)
            
            if updated_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logger.info(f"Successfully audited and improved: {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
        
        return False

    def _fix_deprecated_replacements(self, content: str) -> str:
        """Fixes fragile string replaces for SOH delimiters where applicable."""
        # Example safety patch: ensure raw string replacements for checksums use proper byte formatting
        # or convert old pipe-delimited string hacks to robust SOH handling.
        old_pattern = 'raw_message.replace("|", "\\x01")'
        new_pattern = 'raw_message  # Delimiters handled via native \\x01 bytes'
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
        return content

    def _ensure_future_imports(self, content: str) -> str:
        """Ensures modern Python type hinting annotations are supported if missing."""
        if "from __future__ import annotations" not in content and "def " in content:
            # Prepend future annotations for clean type Hint evaluation
            lines = content.splitlines()
            # Insert after initial module docstring or imports
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i
                    break
            lines.insert(insert_idx, "from __future__ import annotations")
            content = "\n".join(lines) + "\n"
        return content

if __name__ == "__main__":
    auditor = RepositoryAuditor()
    auditor.audit_and_fix()
