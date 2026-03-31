"""
LSP Client - Language Server Protocol integration for IDE precision.

Features:
- Workspace rename (rename symbol across all files)
- Pre-build diagnostics (errors, warnings, hints)
- Go to definition
- Find all references
- Auto-completion

Supports: Python (pylsp), TypeScript (typescript-language-server)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid


@dataclass
class LSPPosition:
    """Position in a document (0-indexed)."""
    line: int
    character: int
    
    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "character": self.character}


@dataclass
class LSPRange:
    """Range in a document."""
    start: LSPPosition
    end: LSPPosition
    
    def to_dict(self) -> Dict[str, Dict]:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }


@dataclass
class LSPDiagnostic:
    """Diagnostic (error/warning/hint) from LSP."""
    file_path: str
    line: int
    column: int
    message: str
    severity: str  # "error", "warning", "information", "hint"
    source: str = ""
    code: str = ""
    
    def __str__(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}: {self.severity}: {self.message}"


@dataclass
class LSPDefinition:
    """Definition location from LSP."""
    file_path: str
    line: int
    column: int
    end_line: int = 0
    end_column: int = 0
    
    def to_location(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}"


@dataclass
class LSPReference:
    """Reference location from LSP."""
    file_path: str
    line: int
    column: int
    line_content: str = ""


@dataclass
class LSPRenameResult:
    """Result of a rename operation."""
    success: bool
    old_name: str
    new_name: str
    changes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    error: str = ""


class LSPClient:
    """
    LSP client for IDE-precision code operations.
    
    Usage:
        client = LSPClient("python")
        await client.start()
        
        # Get diagnostics
        diagnostics = await client.get_diagnostics("file.py")
        
        # Go to definition
        definition = await client.go_to_definition("file.py", 10, 5)
        
        # Find references
        references = await client.find_references("file.py", 10, 5)
        
        # Rename symbol
        result = await client.rename("file.py", 10, 5, "new_name")
        
        await client.stop()
    """
    
    LANGUAGE_SERVERS = {
        "python": ["pylsp", "--stdio"],
        "typescript": ["typescript-language-server", "--stdio"],
        "javascript": ["typescript-language-server", "--stdio"],
        "rust": ["rust-analyzer", "--stdio"],
        "go": ["gopls", "--stdio"],
        "java": ["jdtls", "--stdio"],
    }
    
    SEVERITY_MAP = {
        1: "error",
        2: "warning",
        3: "information",
        4: "hint",
    }
    
    def __init__(self, language: str, workspace_root: Optional[str] = None):
        self.language = language.lower()
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self._proc: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._initialized = False
        self._reader_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        """Start the LSP server."""
        if self.language not in self.LANGUAGE_SERVERS:
            raise ValueError(f"Unsupported language: {self.language}")
        
        cmd = self.LANGUAGE_SERVERS[self.language]
        
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.workspace_root),
            )
        except FileNotFoundError:
            # Server not installed, use fallback
            self._proc = None
            return False
        
        # Start reading responses
        self._reader_task = asyncio.create_task(self._read_responses())
        
        # Initialize LSP
        await self._initialize()
        
        return True
    
    async def stop(self):
        """Stop the LSP server."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        if self._proc:
            # Send shutdown request
            try:
                await self._send_request("shutdown", {})
                await self._send_notification("exit", {})
            except:
                pass
            
            self._proc.terminate()
            self._proc.wait(timeout=5)
            self._proc = None
    
    async def _initialize(self):
        """Initialize LSP connection."""
        root_uri = self.workspace_root.as_uri()
        
        result = await self._send_request("initialize", {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "definition": {"linkSupport": True},
                    "references": {"dynamicRegistration": True},
                    "rename": {"dynamicRegistration": True, "prepareSupport": True},
                    "diagnostic": {"dynamicRegistration": True},
                },
                "workspace": {
                    "workspaceEdit": {"documentChanges": True},
                    "symbol": {"dynamicRegistration": True},
                },
            },
        })
        
        if result:
            self._initialized = True
            await self._send_notification("initialized", {})
    
    async def _send_request(self, method: str, params: Dict) -> Any:
        """Send a request to LSP server and wait for response."""
        if not self._proc:
            return None
        
        self._request_id += 1
        request_id = self._request_id
        
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        
        # Create future for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_requests[request_id] = future
        
        # Send request
        try:
            self._proc.stdin.write(header.encode())
            self._proc.stdin.write(content.encode())
            self._proc.stdin.flush()
        except Exception as e:
            del self._pending_requests[request_id]
            return None
        
        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            return None
    
    async def _send_notification(self, method: str, params: Dict):
        """Send a notification (no response expected)."""
        if not self._proc:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        
        try:
            self._proc.stdin.write(header.encode())
            self._proc.stdin.write(content.encode())
            self._proc.stdin.flush()
        except:
            pass
    
    async def _read_responses(self):
        """Read responses from LSP server."""
        if not self._proc:
            return
        
        buffer = b""
        
        while True:
            try:
                # Read Content-Length header
                while b"\r\n\r\n" not in buffer:
                    chunk = self._proc.stdout.read(1024)
                    if not chunk:
                        return
                    buffer += chunk
                
                header_end = buffer.index(b"\r\n\r\n")
                header = buffer[:header_end].decode()
                buffer = buffer[header_end + 4:]
                
                # Parse Content-Length
                content_length = 0
                for line in header.split("\r\n"):
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())
                
                # Read content
                while len(buffer) < content_length:
                    chunk = self._proc.stdout.read(content_length - len(buffer))
                    if not chunk:
                        return
                    buffer += chunk
                
                content = buffer[:content_length]
                buffer = buffer[content_length:]
                
                # Parse message
                message = json.loads(content.decode())
                
                # Handle response
                if "id" in message:
                    request_id = message["id"]
                    if request_id in self._pending_requests:
                        future = self._pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(message.get("result"))
                
            except Exception as e:
                # Error reading, stop
                break
    
    async def open_document(self, file_path: str):
        """Open a document in LSP."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        content = path.read_text(encoding='utf-8', errors='replace')
        
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": path.as_uri(),
                "languageId": self.language,
                "version": 1,
                "text": content,
            }
        })
    
    async def get_diagnostics(self, file_path: str) -> List[LSPDiagnostic]:
        """Get diagnostics (errors, warnings) for a file."""
        if not self._initialized:
            return []
        
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        # Open document first
        await self.open_document(str(path))
        
        # Request diagnostics (method depends on LSP version)
        # Some LSPs send diagnostics automatically on didOpen
        # Others need explicit request
        
        # For now, use pull-diagnostics if available
        try:
            result = await self._send_request("textDocument/diagnostic", {
                "textDocument": {"uri": path.as_uri()}
            })
        except:
            result = None
        
        diagnostics = []
        
        if result and "items" in result:
            for item in result["items"]:
                diag = LSPDiagnostic(
                    file_path=str(path),
                    line=item.get("range", {}).get("start", {}).get("line", 0) + 1,
                    column=item.get("range", {}).get("start", {}).get("character", 0) + 1,
                    message=item.get("message", ""),
                    severity=self.SEVERITY_MAP.get(item.get("severity", 3), "information"),
                    source=item.get("source", ""),
                    code=str(item.get("code", "")),
                )
                diagnostics.append(diag)
        
        return diagnostics
    
    async def go_to_definition(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> Optional[LSPDefinition]:
        """Go to definition at position."""
        if not self._initialized:
            return None
        
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        result = await self._send_request("textDocument/definition", {
            "textDocument": {"uri": path.as_uri()},
            "position": {"line": line - 1, "character": column - 1},
        })
        
        if not result:
            return None
        
        # Handle single result or array
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        elif isinstance(result, dict) and "uri" not in result:
            # LocationLink format
            result = result.get("targetUri", {})
        
        if isinstance(result, dict) and "uri" in result:
            uri = result["uri"]
            range_info = result.get("range", result.get("targetRange", {}))
            start = range_info.get("start", {})
            
            return LSPDefinition(
                file_path=uri.replace("file://", ""),
                line=start.get("line", 0) + 1,
                column=start.get("character", 0) + 1,
            )
        
        return None
    
    async def find_references(
        self,
        file_path: str,
        line: int,
        column: int,
        include_declaration: bool = True,
    ) -> List[LSPReference]:
        """Find all references to symbol at position."""
        if not self._initialized:
            return []
        
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        result = await self._send_request("textDocument/references", {
            "textDocument": {"uri": path.as_uri()},
            "position": {"line": line - 1, "character": column - 1},
            "context": {"includeDeclaration": include_declaration},
        })
        
        references = []
        
        if isinstance(result, list):
            for item in result:
                uri = item.get("uri", "")
                range_info = item.get("range", {})
                start = range_info.get("start", {})
                
                ref = LSPReference(
                    file_path=uri.replace("file://", ""),
                    line=start.get("line", 0) + 1,
                    column=start.get("character", 0) + 1,
                )
                references.append(ref)
        
        return references
    
    async def rename(
        self,
        file_path: str,
        line: int,
        column: int,
        new_name: str,
    ) -> LSPRenameResult:
        """Rename symbol across workspace."""
        if not self._initialized:
            return LSPRenameResult(
                success=False,
                old_name="",
                new_name=new_name,
                error="LSP not initialized",
            )
        
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        result = await self._send_request("textDocument/rename", {
            "textDocument": {"uri": path.as_uri()},
            "position": {"line": line - 1, "character": column - 1},
            "newName": new_name,
        })
        
        if not result:
            return LSPRenameResult(
                success=False,
                old_name="",
                new_name=new_name,
                error="No rename result",
            )
        
        changes = result.get("changes", {})
        
        return LSPRenameResult(
            success=True,
            old_name="",  # Would need to query symbol first
            new_name=new_name,
            changes=changes,
        )
    
    async def get_completion(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> List[Dict[str, Any]]:
        """Get completions at position."""
        if not self._initialized:
            return []
        
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_root / path
        
        result = await self._send_request("textDocument/completion", {
            "textDocument": {"uri": path.as_uri()},
            "position": {"line": line - 1, "character": column - 1},
        })
        
        items = []
        
        if isinstance(result, dict):
            items = result.get("items", [])
        elif isinstance(result, list):
            items = result
        
        return items


# Synchronous wrapper for simple use cases
class LSPClientSync:
    """Synchronous wrapper for LSPClient."""
    
    def __init__(self, language: str, workspace_root: Optional[str] = None):
        self._client = LSPClient(language, workspace_root)
        self._loop = None
    
    def __enter__(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._client.start())
        return self
    
    def __exit__(self, *args):
        self._loop.run_until_complete(self._client.stop())
        self._loop.close()
    
    def get_diagnostics(self, file_path: str) -> List[LSPDiagnostic]:
        return self._loop.run_until_complete(
            self._client.get_diagnostics(file_path)
        )
    
    def go_to_definition(self, file_path: str, line: int, column: int) -> Optional[LSPDefinition]:
        return self._loop.run_until_complete(
            self._client.go_to_definition(file_path, line, column)
        )
    
    def find_references(self, file_path: str, line: int, column: int) -> List[LSPReference]:
        return self._loop.run_until_complete(
            self._client.find_references(file_path, line, column)
        )
    
    def rename(self, file_path: str, line: int, column: int, new_name: str) -> LSPRenameResult:
        return self._loop.run_until_complete(
            self._client.rename(file_path, line, column, new_name)
        )


# CLI test
if __name__ == "__main__":
    print("\n=== LSP Client Test ===\n")
    
    # Check if pylsp is available
    try:
        result = subprocess.run(["which", "pylsp"], capture_output=True)
        has_pylsp = result.returncode == 0
    except:
        has_pylsp = False
    
    if not has_pylsp:
        print("pylsp not installed. Install with: pip install python-lsp-server")
        print("\nRunning mock test...")
        
        # Mock test
        client = LSPClient("python")
        print(f"Language: {client.language}")
        print(f"Supported languages: {list(client.LANGUAGE_SERVERS.keys())}")
        print("\n=== Test Complete (mock) ===")
    else:
        # Real test with a Python file
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def hello():\n')
            f.write('    print("world")\n')
            f.write('    return 42\n')
            f.write('\n')
            f.write('x = hello()\n')
            test_file = f.name
        
        try:
            async def test():
                client = LSPClient("python")
                started = await client.start()
                
                if not started:
                    print("Failed to start LSP server")
                    return
                
                print(f"LSP started: {started}")
                
                # Get diagnostics
                print("\nDiagnostics:")
                diagnostics = await client.get_diagnostics(test_file)
                for d in diagnostics:
                    print(f"  {d}")
                
                # Go to definition
                print("\nGo to definition (line 6, col 5 - 'hello'):")
                definition = await client.go_to_definition(test_file, 6, 5)
                if definition:
                    print(f"  {definition.to_location()}")
                
                # Find references
                print("\nFind references to 'hello':")
                references = await client.find_references(test_file, 1, 5)
                for r in references:
                    print(f"  {r.file_path}:{r.line}")
                
                await client.stop()
                print("\n=== Test Complete ===")
            
            asyncio.run(test())
        finally:
            os.unlink(test_file)
