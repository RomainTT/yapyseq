#!/usr/bin/env python
# coding: utf-8

"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import click
import pkg_resources

from yapyseq import SequenceReader, SequenceFileError, SequenceRunner


@click.group()
def yapyseq_main_cli():
    """Main command line of yapyseq."""
    pass


@yapyseq_main_cli.command()
@click.argument('sequence_file', type=click.Path(exists=True))
def check(sequence_file):
    """Check content validity of a sequence file.

    SEQUENCE_FILE is the path to the sequence file to check.
    """
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


@yapyseq_main_cli.command()
@click.argument('sequence_file', type=click.Path(exists=True))
@click.argument('function_dir', type=click.Path(exists=True))
@click.option('--constant', '-c', multiple=True, type=(str, str, str),
              help=('NAME TYPE VALUE. '
                    'Type must be a valid python built-in type.'))
@click.option('--no-log', is_flag=True,
              help='Use this option to deactivate logging.')
def run(sequence_file, function_dir, constant, no_log):
    """Run a sequence.

    SEQUENCE_FILE is the path to the sequence file to check.
    FUNCTION_DIR is the path to the directory containing Python files
    and functions referenced by the sequence.

    As many constants as wanted can be given. For each constant, you must give
    the name, the type and the value. Example: -c var_name bool True
    """
    constant_dict = {}
    available_types = ['str', 'float', 'int', 'bool']
    # Evaluate every constant value
    for c in constant:
        if c[1] not in available_types:
            raise click.BadOptionUsage(
                option_name='--constant',
                message='Constant type must be in {}'.format(available_types))
        constant_dict[c[0]] = eval('{}("{}")'.format(c[1], c[2]))

    runner = SequenceRunner(sequence_file, function_dir, logger=(not no_log))
    try:
        runner.run(blocking=True)
    except Exception as exc:
        # Log the exceptions if they occur
        runner._logger.exception('An exception was raised during the run'
                                 ' of the sequence.')
        raise exc
