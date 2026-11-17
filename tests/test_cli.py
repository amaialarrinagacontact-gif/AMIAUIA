import json

from amiauia.cli import main


def test_cli_files_json(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("same" * 100)
    (tmp_path / "b.txt").write_text("same" * 100)
    out = tmp_path / "report.json"
    assert main(["files", str(tmp_path), "--json", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert any("duplicate" in f["title"] for f in data["findings"])
    assert "AMIAUIA" in capsys.readouterr().out


def test_cli_missing_path(tmp_path):
    assert main(["files", str(tmp_path / "does_not_exist")]) == 2
