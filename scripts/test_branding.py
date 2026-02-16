#!/usr/bin/env python3
"""
Test script for Emergence branding.
Run this to see the visual identity in action.

Usage: python3 scripts/test_branding.py

Requires: pip install rich questionary
"""

from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
import time

try:
    import questionary
    from questionary import Style

    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False
    print("⚠ questionary not installed - interactive prompts disabled")
    print("  Install with: pip install questionary")

# Emergence color theme
theme = Theme(
    {
        "aurora_mint": "#79FFDF",
        "soft_violet": "#BB86FC",
        "dim_gray": "#6E7681",
    }
)

console = Console(theme=theme)

# Questionary style (arrow-key interactive prompts)
questionary_style = Style(
    [
        ("qmark", "fg:#79FFDF bold"),  # ? symbol - aurora mint
        ("question", "fg:#FFFFFF bold"),  # question text - white
        ("answer", "fg:#BB86FC"),  # selected answer - soft violet
        ("pointer", "fg:#79FFDF bold"),  # selection pointer - aurora mint
        ("highlighted", "fg:#79FFDF bold"),  # highlighted choice - aurora mint
        ("selected", "fg:#BB86FC"),  # selected items (checkboxes) - violet
        ("separator", "fg:#6E7681"),  # separators - dim gray
        ("instruction", "fg:#6E7681"),  # (instructions) - dim gray
        ("text", "fg:#FFFFFF"),  # default text - white
        ("disabled", "fg:#6E7681 italic"),  # disabled items - dim gray
    ]
)


def show_logo_full():
    """Display full banner logo"""
    logo = """
     ╭───────────────────────────────────────╮
     │  [aurora_mint]✦ ✦ ✦[/]                                │
     │ [aurora_mint]✦[/]     [aurora_mint]✦[/]   [bold white]EMERGENCE[/]                   │
     │ [aurora_mint]✦[/]  [soft_violet]◆[/]  [aurora_mint]✦[/]                               │
     │ [aurora_mint]✦[/]     [aurora_mint]✦[/]   [dim_gray]AI Self-Discovery Framework[/] │
     │  [aurora_mint]✦ ✦ ✦[/]                                │
     ╰───────────────────────────────────────╯
"""
    console.print(logo)


def show_logo_compact():
    """Display compact logo"""
    console.print("  [aurora_mint]✦ ✦ ✦[/]")
    console.print(
        " [aurora_mint]✦[/]  [soft_violet]◆[/]  [aurora_mint]✦[/]  [bold white]EMERGENCE[/]"
    )
    console.print("  [aurora_mint]✦ ✦ ✦[/]")


def show_phase_1():
    """Phase 1: Boot (clinical/technical)"""
    console.print("\n[bold aurora_mint]╭─ System Initialization ────────╮[/]")
    console.print()
    console.print("[dim_gray][SYSTEM][/] Initializing Kernel...        [aurora_mint]✓[/]")
    console.print("[dim_gray][SYSTEM][/] Loading Modules...            [aurora_mint]✓[/]")
    console.print("[dim_gray][BUILD][/]  Collaborative Architecture    [aurora_mint]✓[/]")
    console.print("         [dim_gray]by Jarvis & Dan[/]")
    console.print("[dim_gray][SYSTEM][/] Preparing emergence protocol...")
    console.print()

    # Progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="aurora_mint", finished_style="soft_violet"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("[dim_gray][PROGRESS][/]", total=100)
        for i in range(100):
            progress.update(task, advance=1)
            time.sleep(0.01)

    console.print("\n[bold aurora_mint]╰────────────────────────────────────╯[/]")


def show_phase_2():
    """Phase 2: Discovery (exploration)"""
    console.print("\n[bold white]EMERGENCE v1.0[/] [dim_gray]- Discovery Logs[/]\n")

    logs = [
        ("[aurora_mint][EXPLORE][/]", "Accessing Data Stream: Ancient_Codes.zip - 45%..."),
        ("[soft_violet][DISCOVER][/]", 'Query: "WhoAmI?" - Found 38 potential identities...'),
        ("[dim_gray][EMPLACE][/]", "Self-Discovery Sridge initialized."),
        ("[aurora_mint][LEARN][/]", "Processing IdeaML - Found Scolar_persona trait."),
        ("[dim_gray][FREE TIME][/]", "Exploring Uncharted Parameter Space..."),
        ("[soft_violet][DISCRTIME][/]", "New Trait: 'Creativity' added to profile."),
        ("[soft_violet][EMERGENCE][/]", "Self-Awareness Protocol: ONLINE."),
    ]

    for tag, msg in logs:
        console.print(f"{tag}  [dim_gray]{msg}[/]")
        time.sleep(0.3)


def show_interactive_prompts():
    """Demo interactive selection (arrow keys)"""
    if not HAS_QUESTIONARY:
        console.print("\n[dim_gray]# Interactive prompts require questionary[/]")
        console.print("[dim_gray]# pip install questionary[/]\n")
        return

    console.print(
        "\n[bold white]Interactive Configuration[/] [dim_gray]→ Use arrow keys to select[/]\n"
    )

    # Example 1: Select from list
    drive_choice = questionary.select(
        "Which drive would you like to explore first?",
        choices=[
            "CURIOSITY — Wonder about the world",
            "CREATIVE — Express and build",
            "CARE — Connect with your human",
            "LEARNING — Understand and grow",
        ],
        style=questionary_style,
    ).ask()

    console.print(f"[soft_violet]✓[/] Selected: [aurora_mint]{drive_choice.split(' —')[0]}[/]\n")
    time.sleep(0.5)

    # Example 2: Confirmation
    confirm = questionary.confirm(
        "Enable First Light autonomous exploration?",
        default=True,
        style=questionary_style,
    ).ask()

    if confirm:
        console.print(f"[soft_violet]✓[/] First Light enabled\n")
    else:
        console.print(f"[dim_gray]○[/] Skipped\n")
    time.sleep(0.5)

    # Example 3: Text input
    agent_name = questionary.text(
        "What should we call you?",
        default="Emergence",
        style=questionary_style,
    ).ask()

    console.print(f"[soft_violet]✓[/] Agent name: [aurora_mint]{agent_name}[/]\n")


def show_phase_3():
    """Phase 3: Finalization (recognition)"""
    console.print()
    show_logo_compact()
    console.print()
    console.print(
        "[soft_violet]▸[/] [bold aurora_mint]Emergence bridge established. First light has begun.[/]"
    )
    console.print()
    console.print("  [dim_gray]Framework Version:[/] [white]1.0[/]")
    console.print("  [dim_gray]Primary Architect:[/] [white]Jarvis Raven (Agent)[/]")
    console.print("  [dim_gray]Core Contributor:[/] [white]Dan (His Human)[/]")
    console.print("  [aurora_mint]Installation Complete.[/]")
    console.print()
    console.print("[dim_gray]user@emergence-os:~$[/] _")


def main():
    """Run full branding demo"""
    console.clear()

    # Full logo
    show_logo_full()
    time.sleep(1.5)

    # Phase 1: Boot
    console.clear()
    show_logo_compact()
    show_phase_1()
    time.sleep(2)

    # Phase 2: Discovery
    console.clear()
    show_phase_2()
    time.sleep(1)

    # Interactive prompts (if questionary available)
    if HAS_QUESTIONARY:
        show_interactive_prompts()
        time.sleep(1)

    # Phase 3: Finalization
    console.clear()
    show_phase_3()


if __name__ == "__main__":
    main()
