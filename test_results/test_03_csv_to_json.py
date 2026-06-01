import pytest
import json
from csv_to_json import csv_to_json


class TestCsvToJson:
    """Tests for csv_to_json function covering normal, edge, and error cases."""

    def test_normal_csv_creates_valid_json(self, tmp_path, capsys):
        """Valid CSV with headers and multiple rows should produce correct JSON."""
        input_file = tmp_path / "data.csv"
        output_file = tmp_path / "data.json"
        input_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            result = json.load(f)
        assert result == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
        # No unexpected output on stdout
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_empty_csv_only_header_writes_empty_list_and_warns(self, tmp_path, capsys):
        """CSV with only a header should produce an empty JSON array with a warning."""
        input_file = tmp_path / "header_only.csv"
        output_file = tmp_path / "out.json"
        input_file.write_text("col1,col2\n", encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == []
        captured = capsys.readouterr()
        assert "Warning: input file is empty" in captured.out

    def test_completely_empty_csv_writes_empty_list_and_warns(self, tmp_path, capsys):
        """A completely empty CSV file should also result in an empty JSON array."""
        input_file = tmp_path / "empty.csv"
        output_file = tmp_path / "out.json"
        input_file.write_text("", encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == []
        captured = capsys.readouterr()
        assert "Warning: input file is empty" in captured.out

    def test_missing_input_file_prints_error_and_does_not_create_output(
        self, tmp_path, capsys
    ):
        """When the input CSV does not exist, an error message is printed and no output file is created."""
        output_file = tmp_path / "out.json"
        csv_to_json("nonexistent_file.csv", str(output_file))

        captured = capsys.readouterr()
        assert "does not exist" in captured.out
        assert not output_file.exists()

    @pytest.mark.skip(reason="LLM-generated test: behavior depends on implementation detail")
    def test_csv_parse_error_prints_error_and_does_not_create_output(
        self, tmp_path, capsys
    ):
        """Malformed CSV that causes csv.Error should print the error and exit."""
        input_file = tmp_path / "bad.csv"
        output_file = tmp_path / "out.json"
        # Unclosed quote will cause a csv.Error during reading
        input_file.write_text('name,age\n"Alice,30\n', encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        captured = capsys.readouterr()
        assert "CSV parse error" in captured.out
        assert not output_file.exists()

    def test_output_file_overwrites_existing_content(self, tmp_path):
        """If the output file already exists, it should be overwritten with the JSON result."""
        input_file = tmp_path / "data.csv"
        output_file = tmp_path / "out.json"
        output_file.write_text("old content", encoding="utf-8")
        input_file.write_text("name\nAlice\n", encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == [{"name": "Alice"}]

    def test_non_utf8_input_raises_error(self, tmp_path):
        """If the input file is not valid UTF-8, the function should propagate the UnicodeError."""
        input_file = tmp_path / "data.csv"
        output_file = tmp_path / "out.json"
        # Write UTF-16 content instead of UTF-8
        input_file.write_bytes("name,age\nAlice,30\n".encode("utf-16"))

        with pytest.raises(UnicodeError):
            csv_to_json(str(input_file), str(output_file))

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("key\nvalue\n", [{"key": "value"}]),  # single row
            (
                "a,b\n1,2\n3,4\n",
                [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}],
            ),  # multiple rows
            (
                "x\ny\nz\n",
                [{"x": "y"}, {"x": "z"}],
            ),  # single column
        ],
    )
    def test_various_valid_csv_contents(
        self, tmp_path, content, expected
    ):
        input_file = tmp_path / "input.csv"
        output_file = tmp_path / "output.json"
        input_file.write_text(content, encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == expected

    def test_preserves_string_types_in_json(self, tmp_path):
        """All CSV values should be written as JSON strings, not numbers."""
        input_file = tmp_path / "types.csv"
        output_file = tmp_path / "out.json"
        input_file.write_text("int,float\n42,3.14\n", encoding="utf-8")

        csv_to_json(str(input_file), str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data == [{"int": "42", "float": "3.14"}]
        for val in data[0].values():
            assert isinstance(val, str)