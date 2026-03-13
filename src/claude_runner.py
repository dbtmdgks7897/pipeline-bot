import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path

CLAUDE_BIN = "claude"


@dataclass
class ClaudeResult:
    success: bool
    output: str
    error: str
    exit_code: int
    elapsed: float


async def run_claude(command: str, project_path: Path, timeout: int = 300) -> ClaudeResult:
    """asyncio subprocess로 claude CLI 실행. 기본 5분 타임아웃.

    CLAUDECODE 환경변수를 제거하여 중첩 세션 에러를 방지한다.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    start = time.monotonic()

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_BIN, "-p", command,
            "--output-format", "text",
            cwd=str(project_path),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = time.monotonic() - start

        return ClaudeResult(
            success=proc.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace"),
            exit_code=proc.returncode if proc.returncode is not None else -1,
            elapsed=elapsed,
        )

    except asyncio.TimeoutError:
        if proc is not None:
            proc.kill()
            await proc.wait()
        elapsed = time.monotonic() - start
        return ClaudeResult(
            success=False,
            output="",
            error=f"실행 타임아웃 ({timeout}초 초과)",
            exit_code=-1,
            elapsed=elapsed,
        )
