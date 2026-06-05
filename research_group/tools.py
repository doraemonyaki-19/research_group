"""Tool definitions and execution engine for the Researcher agent."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Destructive command guard
# ---------------------------------------------------------------------------

_DESTRUCTIVE_PATTERNS = [
    "rm -rf /",
    "rm -rf C:\\",
    "format ",
    "del /s /q C:\\",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # fork bomb
]


def _is_destructive(command: str) -> bool:
    cmd_lower = command.lower().strip()
    return any(pat.lower() in cmd_lower for pat in _DESTRUCTIVE_PATTERNS)


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool_use schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "bash",
        "description": (
            "Run a shell command in the working directory. "
            "Captures stdout and stderr. Use for running training/evaluation scripts, "
            "analyzing results, installing packages, etc. "
            "Timeout defaults to 600 seconds for long-running experiments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 600).",
                    "default": 600,
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a text file. "
            "Path can be absolute or relative to the working directory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to read.",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to return (default: 500).",
                    "default": 500,
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write or overwrite a file. "
            "Path can be absolute or relative to the working directory. "
            "Use this for creating analysis scripts or modified training code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "List the contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: working directory).",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution engine
# ---------------------------------------------------------------------------

class ToolExecutor:
    def __init__(self, working_dir: str | Path):
        self.working_dir = Path(working_dir).resolve()

    def execute(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return its output as a string."""
        try:
            if tool_name == "bash":
                return self._bash(**tool_input)
            elif tool_name == "read_file":
                return self._read_file(**tool_input)
            elif tool_name == "write_file":
                return self._write_file(**tool_input)
            elif tool_name == "list_dir":
                return self._list_dir(**tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {e}"})

    MAX_BASH_TIMEOUT = 14400  # Hard cap: 4 hours, to allow CPU finetuning

    def _bash(self, command: str, timeout: int = 600) -> str:
        timeout = min(timeout, self.MAX_BASH_TIMEOUT)

        if _is_destructive(command):
            return json.dumps({
                "error": "Refused: command matches destructive pattern.",
                "command": command,
            })

        # Why this implementation isn't `subprocess.run(capture_output=True)`:
        #
        #  1. Pipe-buffer hang on grandchild orphans. With `shell=True` on
        #     Windows, subprocess.run spawns cmd.exe → cmd.exe spawns the
        #     real command. After the timeout fires, run() kills cmd.exe but
        #     the grandchild (e.g., a TimesFM finetune python process) is
        #     orphaned with the inherited stdout/stderr pipe handles.
        #     run.communicate() then blocks forever reading from the pipe
        #     because the orphan keeps writing. Observed in pilot run
        #     b9mhpioer (turn 1: 2h+ wall on a 15-min nominal timeout).
        #
        #  2. Locale-dependent decoding. text=True falls back to
        #     locale.getpreferredencoding(), which on non-English Windows
        #     (cp950 / Big5 here) crashes the reader thread on any UTF-8
        #     byte sequence in tool output.
        #
        # Fix: redirect output to temp files (no pipe-buffer dependency on
        # the orphan), spawn with Popen, and on timeout walk the process
        # tree via Windows `taskkill /F /T` so descendants are killed too.
        out_fd, out_path = tempfile.mkstemp(suffix=".bashout")
        err_fd, err_path = tempfile.mkstemp(suffix=".basherr")
        os.close(out_fd)
        os.close(err_fd)

        timed_out = False
        out_f = err_f = None
        proc = None
        try:
            out_f = open(out_path, "wb")
            err_f = open(err_path, "wb")
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=out_f,
                stderr=err_f,
                cwd=str(self.working_dir),
            )
            try:
                returncode = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                returncode = -1
                # Kill the entire process tree, not just cmd.exe.
                # taskkill /F /T walks parent→child links and force-kills
                # all descendants. This is the stdlib equivalent of
                # `psutil.Process.children(recursive=True)` on Windows.
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True,
                            timeout=30,
                        )
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                else:
                    proc.kill()
                # Reap the (now-killed) immediate child so its handles release.
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        except Exception as e:
            output = {"error": str(e), "returncode": -1}
            try:
                if out_f: out_f.close()
                if err_f: err_f.close()
                os.unlink(out_path)
                os.unlink(err_path)
            except Exception:
                pass
            return json.dumps(output)
        finally:
            if out_f: out_f.close()
            if err_f: err_f.close()

        try:
            with open(out_path, encoding="utf-8", errors="replace") as f:
                stdout = f.read()
            with open(err_path, encoding="utf-8", errors="replace") as f:
                stderr = f.read()
        finally:
            try: os.unlink(out_path)
            except Exception: pass
            try: os.unlink(err_path)
            except Exception: pass

        if timed_out:
            output = {
                "stdout": stdout[-8000:] if len(stdout) > 8000 else stdout,
                "stderr": stderr[-2000:] if len(stderr) > 2000 else stderr,
                "error": f"Command timed out after {timeout}s; process tree killed",
                "returncode": -1,
            }
        else:
            output = {
                "stdout": stdout[-8000:] if len(stdout) > 8000 else stdout,
                "stderr": stderr[-2000:] if len(stderr) > 2000 else stderr,
                "returncode": returncode,
            }

        return json.dumps(output)

    def _read_file(self, path: str, max_lines: int = 500) -> str:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.working_dir / file_path

        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if len(lines) > max_lines:
                content = "".join(lines[:max_lines])
                content += f"\n... [truncated: {len(lines) - max_lines} more lines]"
            else:
                content = "".join(lines)

            return json.dumps({"content": content, "lines": len(lines), "path": str(file_path)})
        except FileNotFoundError:
            return json.dumps({"error": f"File not found: {file_path}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _write_file(self, path: str, content: str) -> str:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.working_dir / file_path

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"success": True, "path": str(file_path), "bytes": len(content)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _list_dir(self, path: str = ".") -> str:
        dir_path = Path(path)
        if not dir_path.is_absolute():
            dir_path = self.working_dir / dir_path

        try:
            entries = []
            for item in sorted(dir_path.iterdir()):
                kind = "dir" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else None
                entries.append({"name": item.name, "type": kind, "size": size})
            return json.dumps({"path": str(dir_path), "entries": entries})
        except FileNotFoundError:
            return json.dumps({"error": f"Directory not found: {dir_path}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
