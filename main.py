import argparse
import sys
import multiprocessing
import os

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
        print("v1.0.0")

    cpu_affinity = os.sched_getaffinity(0)

    print("System information:")
    print("==========================")
    print("   multiprocessing.cpu_count: %r" % multiprocessing.cpu_count())
    print("      os affinity: %r" % cpu_affinity)
    print("==========================")
    print()

    container = OSContainer()
    container.print()


if __name__ == "__main__":
    main(sys.argv[1:])
