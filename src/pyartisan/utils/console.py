import click


def success(msg: str) -> None:
    click.echo(f"  {msg}")


def warn(msg: str) -> None:
    click.echo(f"⚠ {msg}")


def error(msg: str) -> None:
    click.echo(f"❌ {msg}")
