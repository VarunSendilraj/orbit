"""File system operations for Orbit Agent."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def read_file(path: str) -> Dict[str, Any]:
    """
    Read text content from a file.

    Args:
        path: File path (supports ~ expansion)

    Returns:
        Dict with success status and file content or error
    """
    try:
        file_path = Path(os.path.expanduser(path))

        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "path": str(file_path),
            }

        if not file_path.is_file():
            return {
                "success": False,
                "error": f"Path is not a file: {file_path}",
                "path": str(file_path),
            }

        content = file_path.read_text(encoding="utf-8")

        return {
            "success": True,
            "content": content,
            "path": str(file_path),
            "size": file_path.stat().st_size,
        }

    except UnicodeDecodeError:
        return {"success": False, "error": f"File is not valid UTF-8 text: {path}", "path": path}
    except Exception as e:
        return {"success": False, "error": str(e), "path": path}


def write_file(path: str, content: str, append: bool = False) -> Dict[str, Any]:
    """
    Write text content to a file.

    Args:
        path: File path (supports ~ expansion)
        content: Text content to write
        append: If True, append to existing file; if False, overwrite

    Returns:
        Dict with success status and file info
    """
    try:
        file_path = Path(os.path.expanduser(path))

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if append:
            file_path.write_text(file_path.read_text(encoding="utf-8") + content, encoding="utf-8")
        else:
            file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "mode": "append" if append else "write",
        }

    except Exception as e:
        return {"success": False, "error": str(e), "path": path}


def list_directory(path: str = ".", pattern: Optional[str] = None) -> Dict[str, Any]:
    """
    List files and directories in a given path.

    Args:
        path: Directory path (supports ~ expansion)
        pattern: Optional glob pattern to filter results

    Returns:
        Dict with success status and list of entries
    """
    try:
        dir_path = Path(os.path.expanduser(path))

        if not dir_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {dir_path}",
                "path": str(dir_path),
            }

        if not dir_path.is_dir():
            return {
                "success": False,
                "error": f"Path is not a directory: {dir_path}",
                "path": str(dir_path),
            }

        if pattern:
            entries = list(dir_path.glob(pattern))
        else:
            entries = list(dir_path.iterdir())

        # Sort entries: directories first, then files, alphabetically
        entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        result_entries = []
        for entry in entries:
            try:
                stat = entry.stat()
                result_entries.append(
                    {
                        "name": entry.name,
                        "path": str(entry),
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size if entry.is_file() else None,
                        "modified": stat.st_mtime,
                    }
                )
            except OSError:
                # Skip entries we can't stat (permissions, etc.)
                continue

        return {
            "success": True,
            "path": str(dir_path),
            "entries": result_entries,
            "count": len(result_entries),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "path": path}


def make_directory(path: str, parents: bool = True) -> Dict[str, Any]:
    """
    Create a directory.

    Args:
        path: Directory path (supports ~ expansion)
        parents: If True, create parent directories as needed

    Returns:
        Dict with success status and directory info
    """
    try:
        dir_path = Path(os.path.expanduser(path))

        if dir_path.exists():
            if dir_path.is_dir():
                return {"success": True, "path": str(dir_path), "existed": True}
            else:
                return {
                    "success": False,
                    "error": f"Path exists but is not a directory: {dir_path}",
                    "path": str(dir_path),
                }

        dir_path.mkdir(parents=parents, exist_ok=True)

        return {"success": True, "path": str(dir_path), "existed": False}

    except Exception as e:
        return {"success": False, "error": str(e), "path": path}


def move_file(source: str, destination: str) -> Dict[str, Any]:
    """
    Move or rename a file/directory.

    Args:
        source: Source path (supports ~ expansion)
        destination: Destination path (supports ~ expansion)

    Returns:
        Dict with success status and paths
    """
    try:
        source_path = Path(os.path.expanduser(source))
        dest_path = Path(os.path.expanduser(destination))

        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source path not found: {source_path}",
                "source": str(source_path),
            }

        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(dest_path))

        return {"success": True, "source": str(source_path), "destination": str(dest_path)}

    except Exception as e:
        return {"success": False, "error": str(e), "source": source, "destination": destination}


def delete_file(path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    Delete a file or directory.

    Args:
        path: Path to delete (supports ~ expansion)
        recursive: If True, delete directories recursively

    Returns:
        Dict with success status and path info
    """
    try:
        file_path = Path(os.path.expanduser(path))

        if not file_path.exists():
            return {
                "success": True,  # Already doesn't exist
                "path": str(file_path),
                "existed": False,
            }

        if file_path.is_file() or file_path.is_symlink():
            file_path.unlink()
            file_type = "file"
        elif file_path.is_dir():
            if recursive:
                shutil.rmtree(str(file_path))
                file_type = "directory"
            else:
                file_path.rmdir()  # Only works if empty
                file_type = "directory"
        else:
            return {
                "success": False,
                "error": f"Unknown file type: {file_path}",
                "path": str(file_path),
            }

        return {"success": True, "path": str(file_path), "type": file_type, "existed": True}

    except Exception as e:
        return {"success": False, "error": str(e), "path": path}


def reveal_in_finder(path: str) -> Dict[str, Any]:
    """
    Reveal a file or directory in macOS Finder.

    Args:
        path: Path to reveal (supports ~ expansion)

    Returns:
        Dict with success status and path info
    """
    try:
        file_path = Path(os.path.expanduser(path))

        if not file_path.exists():
            return {
                "success": False,
                "error": f"Path not found: {file_path}",
                "path": str(file_path),
            }

        # Use 'open -R' to reveal in Finder
        subprocess.run(["open", "-R", str(file_path)], check=True)

        return {"success": True, "path": str(file_path)}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Failed to reveal in Finder: {e}", "path": path}
    except Exception as e:
        return {"success": False, "error": str(e), "path": path}
