#!/usr/env/python
# coding: utf-8

# ------------------------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------------------------

import argparse

# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def get_arguments() -> argparse.Namespace:
    """Get arguments from console

    Return:
        An instance of argparse.Namespace containing parsed arguments as
        attributes of this instance.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("seq_path", help="Path to the sequence to run.")

    args = parser.parse_args()
    return args


def main():
    """The main function that is run when yapyseq is called"""
    args = get_arguments()


# ------------------------------------------------------------------------------
# SCRIPT EXECUTION
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    """The main script which is run when yapyseq is called to run a sequence.
    
    It is the script that launches the rest of the program.
    """
    main()
