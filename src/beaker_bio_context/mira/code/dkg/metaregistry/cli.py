# -*- coding: utf-8 -*-

"""Run the MIRA metaregistry from a custom configuration file."""

from pathlib import Path

import click
from more_click import run_app, with_gunicorn_option, workers_option

from mira.dkg.metaregistry.utils import get_app

__all__ = ["main"]


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, type=int, show_default=True)
@click.option("--config", type=Path, help="Path to custom metaregistry configuration.")
@click.option("--client-base-url", default="", envvar="BASE_URL",
              help="Domain name for deployment e.g.: "
                   "d1t1rcuq5sa4r0.cloudfront.net")
@click.option("--root-path", default="", envvar="ROOT_PATH",
              help="Set a different root path than the default, e.g. when "
                   "running behind a proxy. The root path can also be set "
                   "via the environment using 'ROOT_PATH' for use in e.g. a "
                   "docker. If both are set, the --root-path option takes "
                   "precedence over 'ROOT_PATH'. Note that setting this "
                   "assumes that the prefixed path *is* forwarded to the "
                   "app, meaning the proxy server (cloudfront, nginx) "
                   "*should not* strip the prefix, which is normally what's "
                   "done.")
@workers_option
@with_gunicorn_option
def main(
    host: str,
    port: int,
    config: Path,
    client_base_url: str,
    root_path: str,
    with_gunicorn: bool,
    workers: int,
):
    """Run a custom Bioregistry instance based on a MIRA DKG."""
    if root_path:
        click.echo(f"Using root path {root_path}")

    if client_base_url:
        click.echo(f"Domain name set to {client_base_url}")

    app = get_app(
        config=config, root_path=root_path, client_base_url=client_base_url
    )
    run_app(app, host=host, port=str(port), with_gunicorn=with_gunicorn, workers=workers)


if __name__ == "__main__":
    main()
