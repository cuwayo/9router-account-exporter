import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from importlib import import_module

exporter = import_module("router_account_exporter")
tui = import_module("router_account_exporter.tui")


class ExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = [
            {"id": "account-1", "provider": "github", "name": "First", "accessToken": "secret"},
            {"id": "account-2", "provider": "codex", "name": "Second", "refreshToken": "secret-2"},
        ]
        self.backup = {"providerConnections": self.accounts, "settings": {"theme": "dark"}}

    def test_load_backup_returns_provider_connections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.json"
            path.write_text(json.dumps(self.backup), encoding="utf-8")

            self.assertEqual(exporter.load_accounts(path), self.accounts)

    def test_load_backup_rejects_invalid_collection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.json"
            path.write_text(json.dumps({"providerConnections": {}}), encoding="utf-8")

            with self.assertRaises(exporter.ExportError):
                exporter.load_accounts(path)

    def test_parse_selection_supports_ranges_and_rejects_invalid_values(self) -> None:
        self.assertEqual(exporter.parse_selection("1, 3-4", 4), [0, 2, 3])
        for selection in ("", "0", "5", "1-3,2", "two"):
            with self.subTest(selection=selection), self.assertRaises(exporter.ExportError):
                exporter.parse_selection(selection, 4)

    def test_main_writes_selected_full_records_as_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backup_path = Path(directory) / "backup.json"
            output_path = Path(directory) / "selected.json"
            backup_path.write_text(json.dumps(self.backup), encoding="utf-8")

            with patch.object(exporter.sys.stdin, "isatty", return_value=False), \
                 patch.object(exporter.sys.stdout, "isatty", return_value=False), \
                 redirect_stderr(io.StringIO()):
                status = exporter.main([
                    "--input", str(backup_path), "--output", str(output_path), "--select", "2"
                ])

            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), [self.accounts[1]])

    def test_main_requires_selection_without_tty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backup_path = Path(directory) / "backup.json"
            output_path = Path(directory) / "selected.json"
            backup_path.write_text(json.dumps(self.backup), encoding="utf-8")

            with patch.object(exporter.sys.stdin, "isatty", return_value=False), \
                 patch.object(exporter.sys.stdout, "isatty", return_value=False), \
                 redirect_stderr(io.StringIO()):
                status = exporter.main(["--input", str(backup_path), "--output", str(output_path)])

            self.assertEqual(status, 2)
            self.assertFalse(output_path.exists())

    def test_provider_scoped_selection_and_clear(self) -> None:
        selected = tui.selection_for_provider(self.accounts, set(), "github")
        self.assertEqual(selected, {0})
        selected = tui.selection_for_provider(self.accounts, selected, "codex")
        self.assertEqual(selected, {0, 1})
        self.assertEqual(tui.deselection_for_provider(self.accounts, selected, "github"), {1})

    def test_tui_select_all_and_clear_all(self) -> None:
        app = tui.AccountPicker(self.accounts)

        async def exercise() -> None:
            async with app.run_test() as pilot:
                app.action_select_all()
                self.assertEqual(app.selected_ids, {0, 1})
                app.action_clear_all()
                self.assertEqual(app.selected_ids, set())
                await pilot.pause()

        import asyncio
        asyncio.run(exercise())

    def test_main_rejects_source_as_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backup_path = Path(directory) / "backup.json"
            backup_path.write_text(json.dumps(self.backup), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                status = exporter.main([
                    "--input", str(backup_path), "--output", str(backup_path), "--select", "1"
                ])

            self.assertEqual(status, 2)
            self.assertEqual(json.loads(backup_path.read_text(encoding="utf-8")), self.backup)


if __name__ == "__main__":
    unittest.main()
