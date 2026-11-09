"""Terminal input/output behind a tiny interface, so sessions can be scripted in tests."""

from __future__ import annotations

from typing import Protocol

from rich.console import Console


class IO(Protocol):
    def ask(self, prompt: str) -> str | None:
        """One line of input, or None when the input has ended (Ctrl-D)."""

    def say(self, text: str = "") -> None: ...


class ConsoleIO:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def ask(self, prompt: str) -> str | None:
        try:
            return self.console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    def say(self, text: str = "") -> None:
        self.console.print(text)


class ScriptedIO:
    """Feeds prepared answers and records everything that was shown."""

    def __init__(self, answers: list[str]) -> None:
        self._answers = list(answers)
        self.transcript: list[str] = []

    def ask(self, prompt: str) -> str | None:
        answer = self._answers.pop(0) if self._answers else None
        self.transcript.append(f"{prompt}{'<end of input>' if answer is None else answer}")
        return answer

    def say(self, text: str = "") -> None:
        self.transcript.append(text)
