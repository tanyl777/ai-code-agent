import csv
import json
import os
import io


def csv_to_json(input_path: str, output_path: str) -> None:
    """Read a CSV file and write its contents as JSON.

    Handles missing file, CSV parse errors, and empty input.
    """
    if not os.path.isfile(input_path):
        print(f"Error: file '{input_path}' does not exist")
        return

    try:
        with io.open(input_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
    except csv.Error as e:
        print(f"CSV parse error: {e}")
        return

    if not rows:
        print("Warning: input file is empty or contains only headers")
        rows = []

    with io.open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Create a temporary CSV for demonstration
    test_csv = "temp_demo.csv"
    test_json = "temp_demo.json"
    with io.open(test_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age"])
        writer.writerow(["Alice", 30])
        writer.writerow(["Bob", 25])

    csv_to_json(test_csv, test_json)

    with io.open(test_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]

    # Test missing file
    csv_to_json("nonexistent.csv", "out.json")

    # Cleanup
    os.remove(test_csv)
    os.remove(test_json)
    print("All tests passed")