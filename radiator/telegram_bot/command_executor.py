"""Command executor for running make commands from Telegram bot."""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executor for running make commands."""

    def __init__(self, project_root: Path = None):
        """
        Initialize command executor.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.venv_python = self.project_root / "venv" / "bin" / "python"

    async def run_command(
        self, command: str, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """
        Run a command and return success status, stdout, and stderr.

        Args:
            command: Command to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            logger.info(f"Running command: {command}")

            # Change to project directory
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Redirect stderr to stdout to capture all output
                shell=True,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, "", f"Command timed out after {timeout} seconds"

            # Since stderr is redirected to stdout, stderr will be empty
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = ""  # stderr is redirected to stdout

            # Consider command successful if return code is 0 or 2 (warnings)
            # Return code 2 often means warnings but successful execution
            success = process.returncode in [0, 2]
            logger.info(f"Command completed with return code: {process.returncode}")

            return success, stdout_text, stderr_text

        except Exception as e:
            logger.error(f"Error running command '{command}': {e}")
            return False, "", str(e)

    async def run_make_command(self, target: str, **kwargs) -> Tuple[bool, str, str]:
        """
        Run a make command with optional parameters.

        Args:
            target: Make target to run
            **kwargs: Additional parameters to pass to make

        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Build command with parameters
        cmd_parts = ["make", target]

        for key, value in kwargs.items():
            if value is not None:
                # Escape quotes and special characters in the value
                escaped_value = str(value).replace('"', '\\"').replace("'", "\\'")
                cmd_parts.append(f'{key}="{escaped_value}"')

        command = " ".join(cmd_parts)

        # For make commands, combine stdout and stderr since make often outputs to stderr
        success, stdout, stderr = await self.run_command(command)

        # Combine stdout and stderr for make commands since progress bars often go to stderr
        combined_output = ""
        if stdout.strip():
            combined_output += stdout.strip()
        if stderr.strip():
            if combined_output:
                combined_output += "\n" + stderr.strip()
            else:
                combined_output = stderr.strip()

        return success, combined_output, ""

    async def generate_ttm_details_report(self) -> Tuple[bool, str, str]:
        """
        Generate TTM Details report.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        return await self.run_make_command("generate-ttm-details-report")

    async def sync_and_report(self) -> Tuple[bool, str, str]:
        """Sync tracker and generate status report."""
        return await self.run_make_command("sync-and-report")

    async def sync_tracker(self, filter_str: str) -> Tuple[bool, str, str]:
        """
        Sync tracker with custom filter.

        Args:
            filter_str: Filter string for tracker sync

        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Try direct Python execution first for better output capture
        try:
            import subprocess
            import sys

            # Run the sync_tracker module directly
            cmd = [
                sys.executable,
                "-m",
                "radiator.commands.sync_tracker",
                "--filter",
                filter_str,
            ]

            logger.info(f"Running direct command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=300
            )

            # Consider success if return code is 0 or 2 (warnings)
            success = result.returncode in [0, 2]
            logger.info(
                f"Direct command completed with return code: {result.returncode}"
            )

            # Combine stdout and stderr
            combined_output = ""
            if result.stdout.strip():
                combined_output += result.stdout.strip()
            if result.stderr.strip():
                if combined_output:
                    combined_output += "\n" + result.stderr.strip()
                else:
                    combined_output = result.stderr.strip()

            return success, combined_output, ""

        except Exception as e:
            logger.warning(f"Direct execution failed, falling back to make: {e}")
            # Fallback to make command
            return await self.run_make_command("sync-tracker", FILTER=filter_str)

    def get_available_commands(self) -> Dict[str, str]:
        """
        Get list of available commands with descriptions.

        Returns:
            Dictionary of command names and descriptions
        """
        return {
            "generate_time_to_market_teams": "📊 Сгенерировать отчет Time to Market по командам (опционально: long)",
            "sync_and_report": "🔄 Синхронизировать трекер и сгенерировать отчет",
            "sync_tracker": "🔄 Синхронизировать трекер с фильтром (обязательный параметр)",
            "restart_service": "🔄 Перезапустить сервис телеграм бота",
        }

    def format_command_help(self) -> str:
        """
        Format help text for available commands.

        Returns:
            Formatted help text
        """
        commands = self.get_available_commands()
        help_text = "🤖 Доступные команды:\n\n"

        for cmd, desc in commands.items():
            help_text += f"• /{cmd} - {desc}\n"

        help_text += "\n📝 Примеры использования:\n"
        help_text += "• /sync_tracker Queue: CPO Status: In Progress\n"
        help_text += "• /sync_tracker key:CPO-*\n"
        help_text += "• /generate_time_to_market_teams\n"
        help_text += "• /generate_time_to_market_teams long\n"
        help_text += "• /sync_and_report\n"

        return help_text
