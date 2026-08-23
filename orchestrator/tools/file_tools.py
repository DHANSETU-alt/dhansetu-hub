"""
File tools. Every path goes through paths.resolve_in_workspace() first --
these functions never touch a path that hasn't already passed containment.
"""
from .. import config
from . import paths


class ToolError(RuntimeError):
    pass


def _check_not_denied(relative_path: str):
    lowered = relative_path.lower()
    for pattern in config.DENIED_FILENAME_PATTERNS:
        if pattern in lowered:
            raise ToolError(f"refusing to touch a path matching '{pattern}': {relative_path!r}")


def read_file(business_id: int, params: dict) -> dict:
    rel_path = params["path"]
    target = paths.resolve_in_workspace(business_id, rel_path)
    if not target.exists():
        raise ToolError(f"no such file: {rel_path!r}")
    if not target.is_file():
        raise ToolError(f"not a file: {rel_path!r}")
    data = target.read_bytes()[: config.MAX_FILE_READ_BYTES]
    return {"path": rel_path, "content": data.decode("utf-8", errors="replace")}


def write_file(business_id: int, params: dict) -> dict:
    rel_path = params["path"]
    content = params.get("content", "")
    _check_not_denied(rel_path)

    encoded = content.encode("utf-8")
    if len(encoded) > config.MAX_FILE_WRITE_BYTES:
        raise ToolError(
            f"write of {len(encoded)} bytes exceeds the {config.MAX_FILE_WRITE_BYTES}-byte limit"
        )

    target = paths.resolve_in_workspace(business_id, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded)
    return {"path": rel_path, "bytes_written": len(encoded)}


def list_dir(business_id: int, params: dict) -> dict:
    rel_path = params.get("path", ".")
    target = paths.resolve_in_workspace(business_id, rel_path)
    if not target.exists():
        raise ToolError(f"no such directory: {rel_path!r}")
    if not target.is_dir():
        raise ToolError(f"not a directory: {rel_path!r}")

    entries = []
    for i, child in enumerate(sorted(target.iterdir())):
        if i >= config.MAX_LIST_ENTRIES:
            break
        entries.append({"name": child.name, "is_dir": child.is_dir()})
    return {"path": rel_path, "entries": entries}
