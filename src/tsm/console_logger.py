from rich.console import Console

console = Console()


def log_info(message: str) -> None:
    console.print(f"[bold green]INFO[/bold green] {message}")


def log_error(message: str) -> None:
    console.print(f"[bold red]ERROR[/bold red] {message}")
