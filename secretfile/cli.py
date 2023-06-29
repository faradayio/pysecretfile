from typing import List
import click

from secretfile.secretfile import Secretfile


@click.group()
def main():
    pass


@main.command()
@click.option('--ignore', '-i', multiple=True, help="Ignore a key in the Secretfile.")
def read(ignore: List[str]):
    """Reads the Secretfile and prints out the values in a form which can be `source`d in a shell."""
    for key, value in Secretfile.items():
        if key in ignore:
            continue
        click.echo(f"export {key}={value}")
