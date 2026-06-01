import os
import re
from typing import List, Optional
import pandas as pd


def clean_name(name: str) -> str:
    """Clean a Chinese name by removing whitespace and special characters."""
    if not isinstance(name, str):
        return ""
    # Remove leading/trailing whitespace
    name = name.strip()
    # Remove any non-Chinese, non-alphanumeric characters except underscore and hyphen
    name = re.sub(r'[^\u4e00-\u9fff\w\-]', '', name)
    # Collapse multiple spaces/underscores/hyphens into one
    name = re.sub(r'[\s_\-]+', '_', name)
    return name.strip('_')


def create_folders_from_excel(file_path: str, column_name: str, base_dir: Optional[str] = None) -> List[str]:
    """Read Chinese names from an Excel column, clean them, and create folders.

    Args:
        file_path: Path to the Excel file.
        column_name: Name of the column containing Chinese names.
        base_dir: Base directory to create folders in. Defaults to current directory.

    Returns:
        List of created folder paths.

    Raises:
        FileNotFoundError: If the Excel file does not exist.
        ValueError: If the specified column is not found.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    df = pd.read_excel(file_path)
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in Excel file. Available columns: {list(df.columns)}")

    if base_dir is None:
        base_dir = os.getcwd()

    created_folders: List[str] = []
    for name in df[column_name].dropna():
        cleaned = clean_name(str(name))
        if not cleaned:
            continue
        folder_path = os.path.join(base_dir, cleaned)
        os.makedirs(folder_path, exist_ok=True)
        created_folders.append(folder_path)

    return created_folders


if __name__ == "__main__":
    # Example usage: create a sample Excel file and test
    import tempfile
    import pandas as pd

    # Create a temporary Excel file with Chinese names
    sample_data = {
        "姓名": [" 张三 ", "李四!", "王五  ", "赵六@2023", "  ", None, "钱七_测试"]
    }
    df = pd.DataFrame(sample_data)
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
        df.to_excel(tmp_path, index=False)

    try:
        # Create folders in a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            folders = create_folders_from_excel(tmp_path, "姓名", base_dir=tmp_dir)
            print(f"Created {len(folders)} folders:")
            for folder in folders:
                print(f"  - {folder}")
                assert os.path.exists(folder), f"Folder {folder} was not created"
            print("All tests passed")
    finally:
        os.unlink(tmp_path)