import logging
from typing import Any, List, Optional, TextIO, cast

import click
from requests import HTTPError

from ggshield.cmd.hmsl.hmsl_common_options import (
    full_hashes_option,
    input_arg,
    input_type_option,
    naming_strategy_option,
)
from ggshield.cmd.utils.common_options import add_common_options, json_option
from ggshield.core.config import Config
from ggshield.core.errors import UnexpectedError
from ggshield.core.text_utils import display_info, pluralize
from ggshield.verticals.hmsl import Secret, get_client
from ggshield.verticals.hmsl.collection import (
    InputType,
    NamingStrategy,
    collect,
    prepare,
)
from ggshield.verticals.hmsl.output import show_results


logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@add_common_options()
@json_option
@full_hashes_option
@naming_strategy_option
@input_type_option
@input_arg
def check_cmd(
    ctx: click.Context,
    path: str,
    full_hashes: bool,
    naming_strategy: NamingStrategy,
    input_type: InputType,
    json_output: bool,
    **kwargs: Any,
) -> int:
    """
    Check if secrets have leaked in one command.
    """

    # Collect secrets
    display_info("Collecting secrets...")
    input = cast(TextIO, click.open_file(path, "r"))
    secrets = list(collect(input, input_type))
    # full_hashes is True because we need the hashes to decrypt the secrets.
    # They will correctly be truncated by our client later.
    prepared_data = prepare(secrets, naming_strategy, full_hashes=True)
    display_info(f"Collected {len(prepared_data.payload)} secrets.")

    # Query the API
    display_info("Querying HasMySecretLeaked...")
    config: Config = ctx.obj["config"]
    client = get_client(config)
    found: List[Secret] = []
    error: Optional[Exception] = None
    try:
        for secret in client.check(prepared_data.payload, full_hashes=full_hashes):
            found.append(secret)
    except (ValueError, HTTPError) as exception:
        error = exception
    display_info(
        f"{client.quota.remaining} {pluralize('credit', client.quota.remaining)} left for today."
    )

    # Display results and error
    show_results(found, prepared_data.mapping, json_output, error=error)
    if error:
        raise UnexpectedError(str(error))

    return 0
