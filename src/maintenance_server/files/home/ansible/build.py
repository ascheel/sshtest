from inventory import Inventory
import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--loglevel",
        help="Logging level.  Options: DEBUG, INFO, WARNING, ERROR, CRITICAL",
        default="INFO"
    )
    parser.add_argument(
        "-u",
        "--update",
        help="Update database based on current AWS inventory.",
        action="store_true"
    )
    parser.add_argument(
        "-s",
        "--ssh",
        help="Export all servers to an ssh_config compatible file."
    )
    parser.add_argument(
        "-a",
        "--ansible",
        help="Export all servers to ansible inventory files."
    )
    parser.add_argument(
        "-c",
        "--compiledates",
        help="Compile all launch and seen times.",
        action="store_true"
    )
    args = parser.parse_args()

    i = Inventory(
        loglevel=args.loglevel,
        update=args.update,
        ssh=args.ssh,
        ansible=args.ansible,
        compiledates=args.compiledates
    )
    
    if not args.update and not args.ssh and not args.ansible and not args.compiledates:
        sys.exit("No options chosen.  Nothing to do.")
    if args.update:
        i.roll()
        i.display_report()
        i.symlink()
    if args.ssh:
        i.export_to_ssh()
    if args.ansible:
        i.export_to_ansible()
    if args.compiledates:
        i.compile_date_data()


if __name__ == "__main__":
    main()
