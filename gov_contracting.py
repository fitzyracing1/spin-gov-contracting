"""spin-gov-contracting: Check SAM"""
import sys

INTRO = (
    "spin-gov-contracting by Joshua Almeida.\n"
    "The checker ships in a pull request. Format checks only prove shape, not that an ID is assigned or active. The NAICS table is sample data, not official SBA standards.\n"
    "Sponsor: https://github.com/sponsors/fitzyracing1"
)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    print(INTRO)
    if argv and argv[0] in ("-h", "--help", "help"):
        print()
        print("Usage: python gov_contracting.py")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
