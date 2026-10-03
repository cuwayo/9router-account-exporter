"""Export selected 9router provider connections from a backup JSON file."""

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .tui import AccountPicker


DEFAULT_BACKUP = (
    Path(__file__).resolve().parents[2]
    / "9router-backup-2026-10-03T04-05-02-837Z.json"
)


class ExportError(Exception):
    """An input, selection, or output error suitable for a CLI message."""


def load_accounts(path: Path) -> list[dict[str, object]]:
    """Load the provider connection records from a 9router backup."""
    try:
        with path.open(encoding="utf-8") as backup_file:
            backup = json.load(backup_file)
    except OSError as error:
        raise ExportError(f"cannot read backup '{path}': {error}") from error
    except json.JSONDecodeError as error:
        raise ExportError(f"invalid JSON in '{path}': {error}") from error

    if not isinstance(backup, dict):
        raise ExportError("backup must contain a JSON object at its root")

    accounts = backup.get("providerConnections")
    if not isinstance(accounts, list):
        raise ExportError("backup is missing the 'providerConnections' array")
    if any(not isinstance(account, dict) for account in accounts):
        raise ExportError("every provider connection must be a JSON object")
    return accounts


def parse_selection(value: str, account_count: int) -> list[int]:
    """Parse comma-separated 1-based indices and inclusive ranges."""
    selected: list[int] = []
    seen: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            raise ExportError("selection cannot contain empty entries")
        parts = token.split("-")
        try:
            if len(parts) == 1:
                first = last = int(parts[0])
            elif len(parts) == 2:
                first, last = map(int, parts)
            else:
                raise ValueError
        except ValueError as error:
            raise ExportError(f"invalid selection '{token}'") from error

        if first < 1 or last < first or last > account_count:
            raise ExportError(
                f"selection '{token}' is outside the valid range 1-{account_count}"
            )
        for index in range(first - 1, last):
            if index in seen:
                raise ExportError(f"account {index + 1} was selected more than once")
            selected.append(index)
            seen.add(index)
    if not selected:
        raise ExportError("select at least one account")
    return selected


def _account_label(index: int, account: dict[str, object]) -> str:
    name = str(account.get("name") or "(unnamed)")
    provider = str(account.get("provider") or "unknown provider")
    account_id = str(account.get("id") or "no id")
    return f"{index}. {name} — {provider} — {account_id}"


def _write_export(accounts: list[dict[str, object]], output_path: Path) -> None:
    try:
        with output_path.open("w", encoding="utf-8") as output_file:
            json.dump(accounts, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except OSError as error:
        raise ExportError(f"cannot write export '{output_path}': {error}") from error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export selected provider accounts from a 9router backup as a JSON array."
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_BACKUP,
        help=f"backup JSON file (default: {DEFAULT_BACKUP})",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("9router-accounts-export.json"),
        help="destination JSON file (default: 9router-accounts-export.json)",
    )
    parser.add_argument(
        "-s", "--select", metavar="INDICES",
        help="select 1-based account numbers, e.g. '1,3-5' (bypasses the TUI)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the account-export CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise ExportError("output path must not overwrite the input backup")

        accounts = load_accounts(args.input)
        if not accounts:
            raise ExportError("backup contains no provider connections")

        if args.select is not None:
            indices = parse_selection(args.select, len(accounts))
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ExportError("interactive TUI requires a terminal; use --select for non-interactive export")
            indices = AccountPicker(accounts).run()
            if indices is None:
                print("Export cancelled.")
                return 0

        selected_accounts = [accounts[index] for index in indices]
        _write_export(selected_accounts, args.output)
        print(f"Exported {len(selected_accounts)} account(s) to {args.output}")
        print("Warning: this export contains credentials; store it securely.", file=sys.stderr)
    except ExportError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
