import logging
import time
from pathlib import Path
from typing import Optional, Union
import builtins

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def safe_read_file(filepath: Union[str, Path], encoding: str = 'utf-8', retries: int = 3) -> str:
    """
    Safely read a file with retries and exponential backoff.

    Handles FileNotFoundError, PermissionError, and UnicodeDecodeError.
    Logs all operations.

    Args:
        filepath: Path to the file to read.
        encoding: File encoding.
        retries: Number of retries upon recoverable errors.

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If permission denied after all retries.
        UnicodeDecodeError: If decoding fails with the given encoding.
    """
    filepath = Path(filepath)
    last_exception: Optional[Exception] = None

    for attempt in range(1 + retries):
        try:
            logger.info(f"Attempt {attempt + 1}: Reading file {filepath}")
            with builtins.open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            logger.info(f"Successfully read {len(content)} characters from {filepath}")
            return content
        except FileNotFoundError as e:
            logger.error(f"File not found: {filepath}")
            raise
        except PermissionError as e:
            logger.warning(f"Permission denied: {filepath}. Retrying...")
            last_exception = e
            if attempt < retries:
                time.sleep(2 ** attempt)
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error with '{encoding}': {e}")
            raise
    logger.error(f"Failed to read {filepath} after {retries} retries")
    raise last_exception  # type: ignore[misc]


if __name__ == "__main__":
    # Example usage
    test_file = "example.txt"
    with builtins.open(test_file, "w", encoding="utf-8") as f:
        f.write("Hello, World!\nThis is a test file.")

    try:
        content = safe_read_file(test_file)
        print("File content:")
        print(content)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        import os
        try:
            os.remove(test_file)
        except FileNotFoundError:
            pass