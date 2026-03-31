"""
Hash-Anchored Edit Tool - Zero stale-line editing.

Every line has a hash anchor for verification.
Prevents editing wrong lines when file changed.
Inspired by oh-my-openagent.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class AnchorLine:
    """Represents an anchored line in a file."""
    
    line_number: int
    content: str
    hash_value: str
    anchor_comment: str = ""
    
    @property
    def anchored_content(self) -> str:
        """Return content with anchor comment."""
        if self.anchor_comment:
            return f"{self.content}  {self.anchor_comment}"
        return f"{self.content}  #ANCHOR:{self.line_number}:{self.hash_value}"
    
    @property
    def clean_content(self) -> str:
        """Return content without anchor."""
        return self.content


@dataclass
class EditResult:
    """Result of a hash-anchored edit operation."""
    
    success: bool
    message: str
    old_hash: str = ""
    new_hash: str = ""
    line_number: int = 0
    changes: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.changes is None:
            self.changes = []


class HashAnchoredEdit:
    """
    Hash-anchored file editing for zero stale-line errors.
    
    Problem: When AI reads a file, then edits based on line numbers,
    the file might have changed between read and write. This causes
    edits to wrong lines (stale-line errors).
    
    Solution: Anchor each line with a content hash. Before editing,
    verify the hash still matches. If not, file was modified - abort.
    
    Usage:
        # Read file with anchors
        editor = HashAnchoredEdit()
        anchored = editor.read_with_anchors("file.py")
        
        # AI sees anchored content
        print(anchored)
        # def hello():  #ANCHOR:1:a3b2c1d4
        #     print("hi")  #ANCHOR:2:e5f6g7h8
        
        # AI wants to edit line 2
        # Must provide the old hash as verification
        result = editor.safe_edit(
            "file.py",
            line_number=2,
            old_hash="e5f6g7h8",
            new_content='    print("hello")'
        )
    """
    
    # Regex pattern for anchor comments
    ANCHOR_PATTERN = re.compile(r'#ANCHOR:(\d+):([a-f0-9]{8})\s*$')
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute MD5 hash of content (first 8 chars)."""
        return hashlib.md5(content.encode('utf-8', errors='replace')).hexdigest()[:8]
    
    @staticmethod
    def compute_block_hash(lines: List[str]) -> str:
        """Compute hash for a block of lines."""
        combined = "\n".join(lines)
        return hashlib.md5(combined.encode('utf-8', errors='replace')).hexdigest()[:12]
    
    def read_with_anchors(self, file_path: Union[str, Path]) -> str:
        """
        Read file and add hash anchors to each line.
        
        Returns content with anchor comments for each line.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=False)
        
        anchored_lines = []
        for i, line in enumerate(lines, 1):
            # Don't add anchor to empty lines
            if not line.strip():
                anchored_lines.append(line)
                continue
            
            # Don't add duplicate anchor if already present
            if self.ANCHOR_PATTERN.search(line):
                anchored_lines.append(line)
                continue
            
            # Compute hash of clean line content
            clean_line = self.ANCHOR_PATTERN.sub('', line).rstrip()
            hash_val = self.compute_hash(clean_line)
            
            # Add anchor comment
            anchored = f"{clean_line}  #ANCHOR:{i}:{hash_val}"
            anchored_lines.append(anchored)
        
        return "\n".join(anchored_lines)
    
    def parse_anchors(self, content: str) -> List[AnchorLine]:
        """Parse anchored content into AnchorLine objects."""
        lines = content.splitlines()
        result = []
        
        for i, line in enumerate(lines, 1):
            match = self.ANCHOR_PATTERN.search(line)
            if match:
                anchor_num = int(match.group(1))
                hash_val = match.group(2)
                clean_content = self.ANCHOR_PATTERN.sub('', line).rstrip()
                
                result.append(AnchorLine(
                    line_number=anchor_num,
                    content=clean_content,
                    hash_value=hash_val,
                    anchor_comment=match.group(0),
                ))
            else:
                result.append(AnchorLine(
                    line_number=i,
                    content=line,
                    hash_value=self.compute_hash(line) if line.strip() else "",
                ))
        
        return result
    
    def verify_line(
        self,
        file_path: Union[str, Path],
        line_number: int,
        expected_hash: str,
    ) -> Tuple[bool, str]:
        """
        Verify that a line's content matches the expected hash.
        
        Returns (verified, current_content).
        """
        path = Path(file_path)
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines()
        
        if line_number < 1 or line_number > len(lines):
            return False, f"Line {line_number} out of range (1-{len(lines)})"
        
        line_content = lines[line_number - 1]
        
        # Remove any existing anchor for comparison
        clean_content = self.ANCHOR_PATTERN.sub('', line_content).rstrip()
        actual_hash = self.compute_hash(clean_content)
        
        if actual_hash == expected_hash:
            return True, clean_content
        
        return False, f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
    
    def safe_edit(
        self,
        file_path: Union[str, Path],
        line_number: int,
        old_hash: str,
        new_content: str,
        preserve_indent: bool = True,
    ) -> EditResult:
        """
        Safely edit a line with hash verification.
        
        Args:
            file_path: Path to file
            line_number: Line number to edit (1-indexed)
            old_hash: Expected hash of current content
            new_content: New content for the line
            preserve_indent: Keep original indentation
        
        Returns:
            EditResult with success status
        """
        path = Path(file_path)
        if not path.exists():
            return EditResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=False)
        
        if line_number < 1 or line_number > len(lines):
            return EditResult(
                success=False,
                message=f"Line {line_number} out of range (1-{len(lines)})",
            )
        
        # Verify hash
        current_line = lines[line_number - 1]
        clean_current = self.ANCHOR_PATTERN.sub('', current_line).rstrip()
        actual_hash = self.compute_hash(clean_current)
        
        if actual_hash != old_hash:
            return EditResult(
                success=False,
                message=f"Hash mismatch - file was modified. Expected {old_hash}, got {actual_hash}",
                old_hash=old_hash,
                new_hash=actual_hash,
                line_number=line_number,
            )
        
        # Preserve indentation if requested
        if preserve_indent and clean_current:
            # Get leading whitespace
            indent_match = re.match(r'^(\s*)', clean_current)
            original_indent = indent_match.group(1) if indent_match else ""
            
            # Get new content's intended indent
            new_indent_match = re.match(r'^(\s*)', new_content)
            new_indent = new_indent_match.group(1) if new_indent_match else ""
            
            # If original had more indent, preserve it
            if len(original_indent) > len(new_indent):
                new_content = original_indent + new_content.lstrip()
        
        # Apply edit
        old_content = lines[line_number - 1]
        lines[line_number - 1] = new_content
        
        # Write back
        new_file_content = "\n".join(lines)
        if content.endswith("\n"):
            new_file_content += "\n"
        
        path.write_text(new_file_content, encoding='utf-8')
        
        return EditResult(
            success=True,
            message=f"Successfully edited line {line_number}",
            old_hash=old_hash,
            new_hash=self.compute_hash(new_content),
            line_number=line_number,
            changes=[{
                "line": line_number,
                "old": old_content,
                "new": new_content,
            }],
        )
    
    def safe_replace_block(
        self,
        file_path: Union[str, Path],
        start_line: int,
        end_line: int,
        old_block_hash: str,
        new_lines: List[str],
    ) -> EditResult:
        """
        Safely replace a block of lines with hash verification.
        
        Args:
            file_path: Path to file
            start_line: First line number (1-indexed)
            end_line: Last line number (inclusive)
            old_block_hash: Expected hash of the block
            new_lines: New lines to insert
        
        Returns:
            EditResult with success status
        """
        path = Path(file_path)
        if not path.exists():
            return EditResult(success=False, message=f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=False)
        
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return EditResult(
                success=False,
                message=f"Invalid line range: {start_line}-{end_line}",
            )
        
        # Get block and verify hash
        block = lines[start_line - 1:end_line]
        actual_hash = self.compute_block_hash(block)
        
        if actual_hash != old_block_hash:
            return EditResult(
                success=False,
                message=f"Block hash mismatch - file was modified",
            )
        
        # Replace block
        old_block = list(block)
        lines[start_line - 1:end_line] = new_lines
        
        # Write back
        new_content = "\n".join(lines)
        if content.endswith("\n"):
            new_content += "\n"
        
        path.write_text(new_content, encoding='utf-8')
        
        return EditResult(
            success=True,
            message=f"Successfully replaced lines {start_line}-{end_line}",
            changes=[{
                "start": start_line,
                "end": end_line,
                "old_lines": old_block,
                "new_lines": new_lines,
            }],
        )
    
    def safe_insert(
        self,
        file_path: Union[str, Path],
        after_line: int,
        after_hash: str,
        new_lines: List[str],
    ) -> EditResult:
        """
        Safely insert lines after a verified line.
        """
        path = Path(file_path)
        if not path.exists():
            return EditResult(success=False, message=f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=False)
        
        if after_line < 0 or after_line > len(lines):
            return EditResult(
                success=False,
                message=f"Invalid line number: {after_line}",
            )
        
        # Verify anchor line (if not inserting at beginning)
        if after_line > 0:
            verified, _ = self.verify_line(file_path, after_line, after_hash)
            if not verified:
                return EditResult(
                    success=False,
                    message=f"Hash verification failed for line {after_line}",
                )
        
        # Insert lines
        insert_position = after_line  # 0-indexed position
        for i, new_line in enumerate(new_lines):
            lines.insert(insert_position + i, new_line)
        
        # Write back
        new_content = "\n".join(lines)
        if content.endswith("\n"):
            new_content += "\n"
        
        path.write_text(new_content, encoding='utf-8')
        
        return EditResult(
            success=True,
            message=f"Successfully inserted {len(new_lines)} lines after line {after_line}",
            changes=[{
                "after_line": after_line,
                "inserted": new_lines,
            }],
        )
    
    def safe_delete(
        self,
        file_path: Union[str, Path],
        line_number: int,
        expected_hash: str,
    ) -> EditResult:
        """
        Safely delete a line with hash verification.
        """
        path = Path(file_path)
        if not path.exists():
            return EditResult(success=False, message=f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=False)
        
        if line_number < 1 or line_number > len(lines):
            return EditResult(
                success=False,
                message=f"Line {line_number} out of range",
            )
        
        # Verify hash
        verified, _ = self.verify_line(file_path, line_number, expected_hash)
        if not verified:
            return EditResult(
                success=False,
                message=f"Hash verification failed",
            )
        
        # Delete line
        deleted = lines.pop(line_number - 1)
        
        # Write back
        new_content = "\n".join(lines)
        if content.endswith("\n"):
            new_content += "\n"
        
        path.write_text(new_content, encoding='utf-8')
        
        return EditResult(
            success=True,
            message=f"Successfully deleted line {line_number}",
            changes=[{
                "line": line_number,
                "deleted": deleted,
            }],
        )
    
    def diff_with_anchors(
        self,
        file_path: Union[str, Path],
        new_content: str,
    ) -> List[Dict[str, Any]]:
        """
        Compare file with new content, showing anchor-based diff.
        
        Returns list of changes needed.
        """
        path = Path(file_path)
        if not path.exists():
            return [{"type": "create", "content": new_content}]
        
        old_anchored = self.read_with_anchors(file_path)
        old_lines = old_anchored.splitlines()
        new_lines = new_content.splitlines()
        
        changes = []
        
        # Simple line-by-line comparison
        max_lines = max(len(old_lines), len(new_lines))
        
        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None
            
            if old_line != new_line:
                change = {
                    "line": i + 1,
                    "type": "modified" if old_line and new_line else ("deleted" if old_line else "added"),
                }
                
                if old_line:
                    # Extract hash from old line
                    match = self.ANCHOR_PATTERN.search(old_line)
                    if match:
                        change["old_hash"] = match.group(2)
                        change["old_content"] = self.ANCHOR_PATTERN.sub('', old_line).rstrip()
                
                if new_line:
                    change["new_content"] = new_line
                    change["new_hash"] = self.compute_hash(new_line)
                
                changes.append(change)
        
        return changes


# Singleton
_editor: Optional[HashAnchoredEdit] = None


def get_hash_editor() -> HashAnchoredEdit:
    """Get singleton HashAnchoredEdit instance."""
    global _editor
    if _editor is None:
        _editor = HashAnchoredEdit()
    return _editor


# Convenience functions
def read_anchored(file_path: str) -> str:
    """Read file with hash anchors."""
    return get_hash_editor().read_with_anchors(file_path)


def safe_edit(file_path: str, line: int, old_hash: str, new_content: str) -> EditResult:
    """Safely edit a line."""
    return get_hash_editor().safe_edit(file_path, line, old_hash, new_content)


# CLI test
if __name__ == "__main__":
    import tempfile
    import os
    
    print("\n=== Hash-Anchored Edit Test ===\n")
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def hello():\n')
        f.write('    print("world")\n')
        f.write('    return 42\n')
        test_file = f.name
    
    try:
        editor = HashAnchoredEdit()
        
        # Read with anchors
        print("1. Reading file with anchors:")
        anchored = editor.read_with_anchors(test_file)
        print(anchored)
        print()
        
        # Parse anchors
        print("2. Parsed anchors:")
        anchors = editor.parse_anchors(anchored)
        for a in anchors:
            if a.hash_value:
                print(f"   Line {a.line_number}: hash={a.hash_value}")
        print()
        
        # Verify line
        print("3. Verifying line 2:")
        verified, msg = editor.verify_line(test_file, 2, anchors[1].hash_value)
        print(f"   Verified: {verified}")
        print()
        
        # Safe edit
        print("4. Safe edit line 2:")
        result = editor.safe_edit(
            test_file,
            line_number=2,
            old_hash=anchors[1].hash_value,
            new_content='    print("hello")',
        )
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print()
        
        # Read updated file
        print("5. Updated file:")
        print(Path(test_file).read_text())
        
        # Try stale edit (should fail)
        print("6. Attempting stale edit with old hash:")
        result = editor.safe_edit(
            test_file,
            line_number=2,
            old_hash=anchors[1].hash_value,  # Old hash
            new_content='    print("stale")',
        )
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print()
        
    finally:
        os.unlink(test_file)
    
    print("=== Test Complete ===")
