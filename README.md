# 9router Account Exporter

A Python CLI for selecting provider accounts from a 9router backup and exporting them as a standalone JSON array. It preserves each selected `providerConnections` record as-is, including credential fields.

## Requirements

- Python 3.14 or later
- [`uv`](https://docs.astral.sh/uv/) (recommended) or another way to install the project and its dependencies

The interactive account picker is powered by [Textual](https://textual.textualize.io/).

## Install

Clone the repository and run the CLI with `uv`:

```sh
uv sync
uv run 9router-account-exporter
```

You can also install the project with `uv tool install .` and then run `9router-account-exporter`.

## Usage

By default, the CLI looks for `9router-backup-2026-10-03T04-05-02-837Z.json` in the repository root and writes `9router-accounts-export.json` to the current directory. Backup files are intentionally not committed; pass `--input` to use your own 9router backup. The CLI opens a full-screen picker showing account name, provider, and ID (never credentials).

- Use Up/Down to move through accounts and Space to toggle the highlighted account.
- Choose a provider in the provider selector to filter the list.
- Use **Select visible** / **Clear visible** (or `a` / `c`) to select or unselect all accounts currently visible. This applies to the current provider filter; choose **All providers** to act on every account.
- Press `e` or choose **Export selected** to export; press `q` or choose **Cancel** to exit without writing.
- The selection count is shown below the account list.

For repeatable use with your own backup, choose paths explicitly:

```sh
uv run 9router-account-exporter \
  --input path/to/9router-backup.json \
  --output path/to/accounts.json
```

For non-interactive use, provide the 1-based account numbers and ranges to export. The CLI does not open the picker when `--select` is given:

```sh
uv run 9router-account-exporter \
  --input path/to/9router-backup.json \
  --output path/to/accounts.json \
  --select 1,3-5
```

The output is an array containing only the selected account objects. Each object retains all of its original fields, including access and refresh tokens. Treat exported files as secrets and store them securely. The tool refuses to use the same path for input and output.

## Development

Run the test suite with:

```sh
uv run python -m unittest discover -s tests
```

## License

This project is licensed under the [MIT License](LICENSE).
