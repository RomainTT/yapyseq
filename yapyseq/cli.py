#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import click
import pkg_resources

from yapyseq import SequenceReader, SequenceFileError


@click.group()
def yapyseq_main_cli():
    """Main command line of yapyseq."""
    pass


@yapyseq_main_cli.command()
@click.argument('sequence_file')
def check(sequence_file):
    """Check content validity of a sequence file."""
    schema = pkg_resources.resource_filename('yapyseq', 'seq_schema.yaml')
    try:
        SequenceReader.check_sequence_file(sequence_file, schema)
    except SequenceFileError as e:  # Must be catch before OSError
        msg = click.style('Sequence file not valid ! See details below.',
                          bold=True, fg='red')
        click.echo(msg)
        click.echo(e)
    except (FileNotFoundError, OSError) as e:
        msg = click.style(('Error while trying to open sequence file ! '
                           'See details below.'),
                          bold=True, fg='red')
        click.echo(msg)
        click.echo(e)
    else:
        msg = click.style('Sequence file is valid !',
                          bold=True, fg='green')
        click.echo(msg)
