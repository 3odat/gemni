from rich.console import Console
from rich.panel import Panel
import json

console = Console()

class log:
    @staticmethod
    def info(msg): console.print(f"[blue]INFO:[/blue] {msg}")
    @staticmethod
    def success(msg): console.print(f"[green]SUCCESS:[/green] {msg}")
    @staticmethod
    def error(msg): console.print(f"[red]ERROR:[/red] {msg}")
    
    @staticmethod
    def section(title):
        console.print(Panel(f"[bold yellow]{title}[/bold yellow]", expand=False))

    @staticmethod
    def print_json(data):
        console.print_json(json.dumps(data))