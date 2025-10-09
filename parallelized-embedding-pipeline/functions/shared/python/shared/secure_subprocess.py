"""
Secure subprocess utilities for safer command execution.
"""
import subprocess
import shlex
import logging
import os
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Whitelist of allowed commands for security
ALLOWED_COMMANDS = {
    'convert',  # ImageMagick convert
    'gs',       # Ghostscript
    'pdftotext', # poppler-utils
    'pdfinfo',   # poppler-utils
}

def run_subprocess_safely(
    command: List[str], 
    timeout: int = 30,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    input_data: Optional[bytes] = None
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with security restrictions.
    
    Args:
        command: List of command and arguments
        timeout: Maximum execution time in seconds
        cwd: Working directory for the command
        env: Environment variables
        input_data: Data to pass to stdin
        
    Returns:
        subprocess.CompletedProcess: The completed process result
        
    Raises:
        ValueError: If command is not allowed
        subprocess.TimeoutExpired: If command times out
        subprocess.CalledProcessError: If command fails
    """
    if not command or not isinstance(command, list):
        raise ValueError("Command must be a non-empty list")
    
    # Check if the base command is allowed
    base_command = os.path.basename(command[0])
    if base_command not in ALLOWED_COMMANDS:
        raise ValueError(f"Command '{base_command}' is not in the allowed list")
    
    # Sanitize environment variables
    if env is None:
        env = {}
    
    # Remove potentially dangerous environment variables
    safe_env = os.environ.copy()
    safe_env.update(env)
    
    # Remove dangerous env vars
    dangerous_vars = ['LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES']
    for var in dangerous_vars:
        safe_env.pop(var, None)
    
    logger.info(f"Running command: {' '.join(shlex.quote(arg) for arg in command)}")
    
    try:
        result = subprocess.run(
            command,
            timeout=timeout,
            cwd=cwd,
            env=safe_env,
            input=input_data,
            capture_output=True,
            check=True
        )
        
        logger.info(f"Command completed successfully")
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"stderr: {e.stderr.decode('utf-8', errors='ignore')}")
        raise

def validate_file_path(file_path: str, allowed_dirs: Optional[List[str]] = None) -> bool:
    """
    Validate that a file path is safe to use.
    
    Args:
        file_path: The file path to validate
        allowed_dirs: List of allowed directory prefixes
        
    Returns:
        bool: True if path is safe, False otherwise
    """
    if not file_path:
        return False
    
    # Resolve the path to prevent directory traversal
    try:
        resolved_path = os.path.realpath(file_path)
    except (OSError, ValueError):
        return False
    
    # Check for directory traversal attempts
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    # Check against allowed directories if specified
    if allowed_dirs:
        for allowed_dir in allowed_dirs:
            if resolved_path.startswith(os.path.realpath(allowed_dir)):
                return True
        return False
    
    return True