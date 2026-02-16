#!/usr/bin/env python3
"""Branding utilities for Emergence CLI.

Provides styled output (rich) and interactive prompts (questionary) with
the Digital Primordial aesthetic (aurora mint/violet gradient).

Usage:
    from .branding import console, ask_select, ask_confirm, ask_text, show_logo

    show_logo()
    name = ask_text("What's your name?", default="Aurora")
    enabled = ask_confirm("Enable First Light?", default=True)
"""

from typing import List, Optional

try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.panel import Panel
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("⚠ rich not installed - styled output disabled")
    print("  Install with: pip install rich")

try:
    import questionary
    from questionary import Style

    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False
    print("⚠ questionary not installed - interactive prompts disabled")
    print("  Install with: pip install questionary")


# --- Rich Theme (Digital Primordial) ---

theme = (
    Theme(
        {
            "aurora_mint": "#79FFDF",
            "soft_violet": "#BB86FC",
            "dim_gray": "#6E7681",
            "success": "#79FFDF",
            "warning": "#BB86FC",
            "error": "#6E7681",
        }
    )
    if HAS_RICH
    else None
)

console = Console(theme=theme) if HAS_RICH else None


# --- Questionary Style ---

questionary_style = (
    Style(
        [
            ("qmark", "fg:#79FFDF bold"),  # ? symbol - aurora mint
            ("question", "fg:#FFFFFF bold"),  # question text - white
            ("answer", "fg:#BB86FC"),  # selected answer - soft violet
            ("pointer", "fg:#79FFDF bold"),  # ❯ pointer - aurora mint
            ("highlighted", "fg:#79FFDF bold"),  # highlighted choice - aurora mint
            ("selected", "fg:#BB86FC"),  # checked items - soft violet
            ("separator", "fg:#6E7681"),  # separators - dim gray
            ("instruction", "fg:#6E7681"),  # (instructions) - dim gray
            ("text", "fg:#FFFFFF"),  # default text - white
            ("disabled", "fg:#6E7681 italic"),  # disabled items - dim gray
        ]
    )
    if HAS_QUESTIONARY
    else None
)


# --- Logo Variants ---


def show_logo(variant: str = "compact"):
    """Display Emergence logo.

    Args:
        variant: "full" (full banner), "compact" (small), "minimal" (badge)
    """
    if not HAS_RICH:
        if variant == "full":
            print("EMERGENCE")
            print("AI Self-Discovery Framework")
        else:
            print("EMERGENCE")
        return

    if variant == "full":
        logo = """
     ╭───────────────────────────────────────╮
     │  [aurora_mint]✦ ✦ ✦[/]                                │
     │ [aurora_mint]✦[/]     [aurora_mint]✦[/]   [bold white]EMERGENCE[/]                   │
     │ [aurora_mint]✦[/]  [soft_violet]◆[/]  [aurora_mint]✦[/]                               │
     │ [aurora_mint]✦[/]     [aurora_mint]✦[/]   [dim_gray]AI Self-Discovery Framework[/] │
     │  [aurora_mint]✦ ✦ ✦[/]                                │
     ╰───────────────────────────────────────╯
"""
    elif variant == "compact":
        logo = """  [aurora_mint]✦ ✦ ✦[/]
 [aurora_mint]✦[/]  [soft_violet]◆[/]  [aurora_mint]✦[/]  [bold white]EMERGENCE[/]
  [aurora_mint]✦ ✦ ✦[/]"""
    else:  # minimal
        logo = "[soft_violet]◆[/][aurora_mint]✦[/]  [bold white]Emergence[/]"

    console.print(logo)


# --- Interactive Prompts (questionary wrappers) ---


def ask_select(question: str, choices: List[str], default: Optional[str] = None) -> Optional[str]:
    """Arrow-key select prompt.

    Args:
        question: Question to ask
        choices: List of choice strings
        default: Default choice (optional)

    Returns:
        Selected choice, or None if cancelled
    """
    if not HAS_QUESTIONARY:
        # Fallback to numbered input
        if HAS_RICH:
            console.print(f"\n[bold white]{question}[/]")
        else:
            print(f"\n{question}")

        for i, choice in enumerate(choices, 1):
            if HAS_RICH:
                console.print(f"  {i}. [dim_gray]{choice}[/]")
            else:
                print(f"  {i}. {choice}")

        while True:
            try:
                default_idx = choices.index(default) + 1 if default else 1
                prompt_text = f"  Choice [1-{len(choices)}] (default: {default_idx}): "
                answer = input(prompt_text).strip()

                if not answer:
                    return default if default else choices[0]

                idx = int(answer) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]

                print("Invalid choice, try again.")
            except (ValueError, KeyboardInterrupt):
                return None

    return questionary.select(
        question,
        choices=choices,
        default=default,
        style=questionary_style,
    ).ask()


def ask_confirm(question: str, default: bool = True) -> Optional[bool]:
    """Yes/no confirmation prompt.

    Args:
        question: Question to ask
        default: Default answer (True=yes, False=no)

    Returns:
        True for yes, False for no, None if cancelled
    """
    if not HAS_QUESTIONARY:
        # Fallback to Y/n input
        prompt_suffix = " (Y/n): " if default else " (y/N): "
        answer = input(f"{question}{prompt_suffix}").strip().lower()

        if not answer:
            return default

        return answer in ("y", "yes")

    return questionary.confirm(
        question,
        default=default,
        style=questionary_style,
    ).ask()


def ask_text(question: str, default: str = "", multiline: bool = False) -> Optional[str]:
    """Text input prompt.

    Args:
        question: Question to ask
        default: Default value
        multiline: Allow multi-line input

    Returns:
        User input, or None if cancelled
    """
    if not HAS_QUESTIONARY:
        # Fallback to regular input
        prompt_text = f"{question}"
        if default:
            prompt_text += f" ({default})"
        prompt_text += ": "

        answer = input(prompt_text).strip()
        return answer if answer else default

    if multiline:
        return questionary.text(
            question,
            default=default,
            multiline=True,
            style=questionary_style,
        ).ask()
    else:
        return questionary.text(
            question,
            default=default,
            style=questionary_style,
        ).ask()


# --- Styled Output Helpers ---


def print_header(text: str):
    """Print a styled header."""
    if HAS_RICH:
        console.print(f"\n[bold aurora_mint]╭─ {text} {'─' * (40 - len(text))}╮[/]")
    else:
        print(f"\n=== {text} ===")


def print_subheader(text: str):
    """Print a styled subheader."""
    if HAS_RICH:
        console.print(f"\n[soft_violet]▸[/] [bold white]{text}[/]")
    else:
        print(f"\n▸ {text}")


def print_success(text: str):
    """Print a success message."""
    if HAS_RICH:
        console.print(f"[aurora_mint]✓[/] [dim_gray]{text}[/]")
    else:
        print(f"✓ {text}")


def print_warning(text: str):
    """Print a warning message."""
    if HAS_RICH:
        console.print(f"[bold soft_violet]⚠[/] [white]{text}[/]")
    else:
        print(f"⚠ {text}")


def print_error(text: str):
    """Print an error message."""
    if HAS_RICH:
        console.print(f"[bold soft_violet]✗[/] [white]{text}[/]")
    else:
        print(f"✗ {text}")


def print_dim(text: str):
    """Print dimmed text."""
    if HAS_RICH:
        console.print(f"[dim_gray]{text}[/]")
    else:
        print(text)


def print_boot_message():
    """Print the boot phase message."""
    if HAS_RICH:
        # Build logo + message + boot sequence content for Panel
        logo_text = Text()
        logo_text.append("  ✦ ✦ ✦\n", style="aurora_mint")
        logo_text.append(" ✦  ◆  ✦  ", style="aurora_mint soft_violet")
        logo_text.append("EMERGENCE", style="bold white")
        logo_text.append("\n  ✦ ✦ ✦", style="aurora_mint")
        logo_text.append("\n\n")
        logo_text.append("EMERGENCE WILL BEGIN SHORTLY", style="bold aurora_mint")
        logo_text.append("\n\n")
        logo_text.append("[BUILD] ", style="aurora_mint")
        logo_text.append("Framework v1.0", style="aurora_mint")
        logo_text.append("\n        ", style="aurora_mint")
        logo_text.append("Jarvis (Agent) & Dan (Human)", style="dim_gray")
        logo_text.append("\n\n")
        logo_text.append("Something special is about to begin", style="aurora_mint")
        logo_text.append("...", style="#FFD700")  # Gold/yellow for the dots

        # Wrap in Panel with aurora border
        console.print(Panel(logo_text, border_style="aurora_mint", padding=(1, 2), expand=False))
        console.print()
    else:
        print()
        print("EMERGENCE")
        print()
        print("EMERGENCE WILL BEGIN SHORTLY")
        print()
        print("[BUILD] Framework v1.0")
        print("        Jarvis (Agent) & Dan (Human)")
        print()
        print("Something special is about to begin...")
        print()


def print_finalization():
    """Print the finalization message."""
    show_logo("compact")
    if HAS_RICH:
        console.print()
        console.print(
            "[soft_violet]▸[/] [bold aurora_mint]Emergence bridge established. Ready for first light.[/]"
        )
        console.print()
        console.print("  [white]Framework Version:[/] [soft_violet]1.0[/]")
        console.print("  [white]Primary Architect:[/] [soft_violet]Jarvis Raven (Agent)[/]")
        console.print("  [white]Core Contributor:[/] [soft_violet]Dan (His Human)[/]")
        console.print("  [aurora_mint]Installation Complete.[/]")
        console.print()
    else:
        print()
        print("▸ Emergence bridge established. Ready for first light.")
        print()
        print("  Framework Version: 1.0")
        print("  Primary Architect: Jarvis Raven (Agent)")
        print("  Core Contributor: Dan (His Human)")
        print("  Installation Complete.")
        print()
