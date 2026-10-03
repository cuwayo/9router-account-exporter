"""Textual account picker for 9router backups."""

from __future__ import annotations

from collections.abc import Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, Select, SelectionList, Static
from textual.widgets.selection_list import Selection


Account = dict[str, object]


def provider_names(accounts: Sequence[Account]) -> list[str]:
    """Return provider names in first-seen order."""
    return list(dict.fromkeys(str(account.get("provider") or "unknown") for account in accounts))


def selection_for_provider(
    accounts: Sequence[Account], selected_ids: set[int], provider: str
) -> set[int]:
    """Return a copy of the selection with all accounts of a provider selected."""
    return selected_ids | {
        index for index, account in enumerate(accounts)
        if str(account.get("provider") or "unknown") == provider
    }


def deselection_for_provider(
    accounts: Sequence[Account], selected_ids: set[int], provider: str
) -> set[int]:
    """Return a copy of the selection with all accounts of a provider cleared."""
    provider_ids = {
        index for index, account in enumerate(accounts)
        if str(account.get("provider") or "unknown") == provider
    }
    return selected_ids - provider_ids


def _label(index: int, account: Account) -> str:
    return "  ".join(
        (
            str(account.get("name") or "(unnamed)"),
            str(account.get("provider") or "unknown"),
            str(account.get("id") or "no id"),
        )
    )


class AccountPicker(App[list[int] | None]):
    """Interactive checkbox picker that returns selected account indices."""

    TITLE = "9router Account Exporter"
    SUB_TITLE = "Select provider accounts to export"
    CSS = """
    Screen { layout: vertical; }
    #intro { height: 1; margin: 0 1; }
    #toolbar { height: 3; margin: 0 1; }
    #provider { width: 34; }
    #bulk { width: auto; }
    #account-list { height: 1fr; margin: 0 1; border: round $primary; }
    #status { height: 1; margin: 0 1; }
    #actions { height: 3; align-horizontal: right; margin: 0 1; }
    #actions Button { margin-left: 1; }
    """
    BINDINGS = [
        Binding("space", "toggle", "Toggle account", show=True),
        Binding("a", "select_all", "Select all", show=True),
        Binding("c", "clear_all", "Clear all", show=True),
        Binding("e", "export", "Export", show=True),
        Binding("q", "cancel", "Quit", show=True),
    ]

    def __init__(self, accounts: Sequence[Account]) -> None:
        super().__init__()
        self.accounts = list(accounts)
        self.selected_ids: set[int] = set()
        self.visible_ids: list[int] = list(range(len(accounts)))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[ ] Toggle with Space · Select/clear visible entries · Credentials are not shown", id="intro")
        with Horizontal(id="toolbar"):
            options = [("All providers", "__all__")] + [
                (provider, provider) for provider in provider_names(self.accounts)
            ]
            yield Select(options, value="__all__", allow_blank=False, id="provider")
            yield Button("Select visible", id="select-visible", variant="primary")
            yield Button("Clear visible", id="clear-visible")
        yield SelectionList(id="account-list")
        yield Static("0 selected", id="status")
        with Horizontal(id="actions"):
            yield Button("Export selected", id="export", variant="success")
            yield Button("Cancel", id="cancel")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_rows()

    def _current_provider(self) -> str:
        value = self.query_one("#provider", Select).value
        return str(value)

    def _refresh_rows(self) -> None:
        provider = self._current_provider()
        self.visible_ids = [
            index for index, account in enumerate(self.accounts)
            if provider == "__all__"
            or str(account.get("provider") or "unknown") == provider
        ]
        rows = self.query_one("#account-list", SelectionList)
        rows.clear_options()
        for index in self.visible_ids:
            selected = index in self.selected_ids
            account = self.accounts[index]
            rows.add_option(Selection(_label(index + 1, account), index, selected))
        self._update_status()

    def _update_status(self) -> None:
        self.query_one("#status", Static).update(
            f"{len(self.selected_ids)} selected / {len(self.accounts)} total"
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        self._refresh_rows()

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled[int]
    ) -> None:
        if event.selection.value in self.selected_ids:
            self.selected_ids.remove(event.selection.value)
        else:
            self.selected_ids.add(event.selection.value)
        self._update_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "select-visible":
            self.selected_ids.update(self.visible_ids)
            self._refresh_rows()
        elif button_id == "clear-visible":
            self.selected_ids.difference_update(self.visible_ids)
            self._refresh_rows()
        elif button_id == "export":
            self.action_export()
        elif button_id == "cancel":
            self.action_cancel()

    def action_toggle(self) -> None:
        self.query_one("#account-list", SelectionList).action_select()

    def action_select_all(self) -> None:
        self.selected_ids.update(self.visible_ids)
        self._refresh_rows()

    def action_clear_all(self) -> None:
        self.selected_ids.difference_update(self.visible_ids)
        self._refresh_rows()

    def action_export(self) -> None:
        if not self.selected_ids:
            self.query_one("#status", Static).update("Select at least one account before exporting")
            return
        self.exit(sorted(self.selected_ids))

    def action_cancel(self) -> None:
        self.exit(None)
