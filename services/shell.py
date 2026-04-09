import asyncio
from dataclasses import dataclass


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


async def run(command: list[str], timeout: float = 30.0) -> CommandResult:
    """Execute a shell command and return its result.

    Args:
        command: Command and arguments as a list, e.g. ["ls", "-la"].
        timeout: Maximum seconds to wait before raising asyncio.TimeoutError.
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise

    return CommandResult(
        returncode=process.returncode,
        stdout=stdout_bytes.decode(),
        stderr=stderr_bytes.decode(),
    )
