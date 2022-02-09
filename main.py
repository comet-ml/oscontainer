import argparse
import sys

import oscontainer
from oscontainer import OSContainer


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--version",
        help="Display version",
        action="store_const",
        const=True,
        default=False,
    )
    args = parser.parse_args(raw_args)
    if args.version:
        print(oscontainer.__version__)

    container = OSContainer()
    container.print()


if __name__ == "__main__":
    main(sys.argv[1:])
