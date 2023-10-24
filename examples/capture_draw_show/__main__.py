#! /usr/bin/env python3

"""
Example of code of capture / draw / show operations.
"""


# Standard Library
import sys

if __name__ == '__main__':
    python_version = sys.version.split()[0]
    if sys.version_info < (3, 9):
        sys.stdout.write(
            f'this example requires Python 3.9+, you are using {python_version}',
            'which is not supported\n',
        )
        sys.exit(1)

    # Third Party
    import run  # pylint: disable=E0401

    run.main()
