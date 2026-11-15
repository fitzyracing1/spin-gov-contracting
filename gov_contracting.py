"""spin-gov-contracting: UEI and CAGE format checks, sample NAICS lookup."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from decimal import Decimal
from pathlib import Path

INTRO = (
    "spin-gov-contracting by Joshua Almeida.\n"
    "Format checks only, no API, offline. Sponsor: https://github.com/sponsors/fitzyracing1"
)

# Published format rules, not a live SAM.gov or DLA lookup.
# UEI: GSA Unique Entity ID stakeholder materials (Nov 2021) describe a
# 12-character alphanumeric value that does not use the letters O or I, and
# whose first character is not zero.
# CAGE: DLA describes a 5-character alphanumeric code excluding I and O, with
# the fifth position numeric for a US CAGE. Official examples include 0YWL3.
# Format-valid does not mean the ID is assigned or active.

UEI_RE = re.compile(r"^[A-HJ-NP-Z0-9]{12}$")
US_CAGE_RE = re.compile(r"^[0-9A-HJ-NP-Z]{4}[0-9]$")
NCAGE_RE = re.compile(r"^[0-9A-HJ-NP-Z]{5}$")
NAICS_RE = re.compile(r"^\d{6}$")
SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "SAMPLE_NAICS_SIZE_STANDARDS.csv"
SAMPLE_DISCLAIMER = (
    "SAMPLE table only — not official SBA size standards. "
    "Do not use this for eligibility, filing, or certification."
)


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def check_uei(value: str) -> dict:
    raw = value.strip()
    code = normalize(raw)
    issues = []
    if not re.fullmatch(r"[A-Za-z0-9]+", raw.replace(" ", "")):
        issues.append("only letters and digits are allowed (no hyphens or punctuation)")
    if len(code) != 12:
        issues.append(f"must be exactly 12 characters, got {len(code)}")
    if any(ch in code for ch in "IO"):
        issues.append("letters I and O are not used (they can be confused with 1 and 0)")
    if code.startswith("0"):
        issues.append("the first character is never zero")
    ok = not issues and bool(UEI_RE.match(code))
    return {
        "kind": "UEI",
        "value": code,
        "ok": ok,
        "issues": issues,
        "note": "Format only; does not prove the ID is assigned or active on SAM.gov.",
        "rules": "12 alphanumeric characters, no I or O, first character is not 0.",
    }


def check_cage(value: str, *, ncage: bool = False) -> dict:
    code = normalize(value)
    issues = []
    if len(code) != 5:
        issues.append(f"must be exactly 5 characters, got {len(code)}")
    if not re.fullmatch(r"[A-Z0-9]*", code):
        issues.append("only letters and digits are allowed")
    if any(ch in code for ch in "IO"):
        issues.append("letters I and O are not used")
    if ncage:
        ok = not issues and bool(NCAGE_RE.match(code))
        kind = "NCAGE"
        rules = "5 alphanumeric characters excluding I and O (NATO NCAGE shape)."
        note = "Format only; this is not a DLA or NSPA assignment check."
    else:
        if code and not code[-1].isdigit():
            issues.append("a US CAGE has a digit in the fifth position (DLA)")
        looks_like_ncage = bool(NCAGE_RE.match(code)) and code and (code[0].isalpha() or code[-1].isalpha())
        ok = not issues and bool(US_CAGE_RE.match(code))
        kind = "CAGE"
        rules = "5 alphanumeric characters excluding I and O, fifth character is a digit (US CAGE, DLA)."
        note = "Format only; verify an assigned code at https://cage.dla.mil."
        if looks_like_ncage and not ok:
            note += " This value may be an NCAGE; retry with --ncage."
    return {
        "kind": kind,
        "value": code,
        "ok": ok,
        "issues": issues,
        "note": note,
        "rules": rules,
    }


def load_sample_naics(path: Path = SAMPLE_PATH) -> dict:
    rows = {}
    with path.open(encoding="utf-8") as handle:
        lines = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    for row in reader:
        rows[row["naics"].strip()] = {
            "naics": row["naics"].strip(),
            "title": row["title"].strip(),
            "size_standard": Decimal(row["size_standard"].strip()),
            "unit": row["unit"].strip(),
        }
    return rows


def lookup_naics(code: str, *, receipts=None, employees=None, table=None) -> dict:
    code = re.sub(r"\D", "", code)
    issues = []
    if not NAICS_RE.match(code):
        issues.append("NAICS codes in this tool are 6 digits")
        return {
            "ok": False,
            "code": code,
            "issues": issues,
            "row": None,
            "comparison": None,
            "disclaimer": SAMPLE_DISCLAIMER,
        }
    table = load_sample_naics() if table is None else table
    row = table.get(code)
    if row is None:
        return {
            "ok": True,
            "code": code,
            "issues": [],
            "row": None,
            "comparison": None,
            "disclaimer": SAMPLE_DISCLAIMER,
            "missing": True,
        }
    comparison = None
    if receipts is not None or employees is not None:
        if row["unit"] == "receipts_usd":
            if receipts is None:
                comparison = "this sample standard is in receipts; pass --receipts to compare"
            else:
                given = Decimal(str(receipts))
                comparison = (
                    "under the sample receipts threshold"
                    if given <= row["size_standard"]
                    else "over the sample receipts threshold"
                )
        else:
            if employees is None:
                comparison = "this sample standard is in employees; pass --employees to compare"
            else:
                given = Decimal(str(employees))
                comparison = (
                    "under the sample employee threshold"
                    if given <= row["size_standard"]
                    else "over the sample employee threshold"
                )
    return {
        "ok": True,
        "code": code,
        "issues": [],
        "row": row,
        "comparison": comparison,
        "disclaimer": SAMPLE_DISCLAIMER,
        "missing": False,
    }


def _print_id(result: dict) -> None:
    status = "ok" if result["ok"] else "invalid format"
    print(f"{result['kind']}  {result['value'] or '(empty)'}  {status}")
    print(f"  rules  {result['rules']}")
    for issue in result["issues"]:
        print(f"  issue  {issue}")
    print(f"  note   {result['note']}")


def _print_naics(result: dict) -> None:
    print(f"NAICS  {result['code'] or '(empty)'}")
    print(f"  {result['disclaimer']}")
    if result["issues"]:
        for issue in result["issues"]:
            print(f"  issue  {issue}")
        return
    if result.get("missing"):
        print("  not in the bundled sample table; that does not mean the code is invalid")
        return
    row = result["row"]
    unit = "USD receipts" if row["unit"] == "receipts_usd" else "employees"
    print(f"  title     {row['title']}")
    print(f"  standard  {row['size_standard']} {unit}  (sample)")
    if result["comparison"]:
        print(f"  compare   {result['comparison']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="gov_contracting.py",
        description="Check UEI and CAGE formats and look up a sample NAICS size table.",
    )
    sub = parser.add_subparsers(dest="cmd")
    uei = sub.add_parser("uei", help="Check Unique Entity ID format (not SAM.gov assignment).")
    uei.add_argument("value")
    cage = sub.add_parser("cage", help="Check CAGE format (not DLA assignment).")
    cage.add_argument("value")
    cage.add_argument("--ncage", action="store_true", help="Use the broader NCAGE 5-character shape.")
    naics = sub.add_parser("naics", help="Look up a SAMPLE size-standard row, not official SBA data.")
    naics.add_argument("code")
    naics.add_argument("--receipts", help="Receipts to compare to a sample receipts threshold.")
    naics.add_argument("--employees", help="Employees to compare to a sample employee threshold.")
    chk = sub.add_parser("check", help="Run UEI, CAGE, and optional NAICS checks together.")
    chk.add_argument("--uei")
    chk.add_argument("--cage")
    chk.add_argument("--ncage", action="store_true")
    chk.add_argument("--naics")
    chk.add_argument("--receipts")
    chk.add_argument("--employees")

    try:
        args = parser.parse_args([] if argv is None and len(sys.argv) == 1 else (sys.argv[1:] if argv is None else argv))
    except SystemExit as exc:
        code = exc.code
        return 0 if code in (0, None) else int(code)

    if not args.cmd:
        print(INTRO)
        print()
        print("Usage: python gov_contracting.py uei J6H4FB3N5YK4")
        print("       python gov_contracting.py cage 0YWL3")
        print("       python gov_contracting.py naics 541511 --receipts 5000000")
        print("       python gov_contracting.py check --uei J6H4FB3N5YK4 --cage 0YWL3 --naics 541511")
        print()
        print("Format-valid is not the same as assigned or active.")
        print(SAMPLE_DISCLAIMER)
        return 0

    print(INTRO)
    print()
    try:
        if args.cmd == "uei":
            result = check_uei(args.value)
            _print_id(result)
            return 0 if result["ok"] else 1
        if args.cmd == "cage":
            result = check_cage(args.value, ncage=args.ncage)
            _print_id(result)
            return 0 if result["ok"] else 1
        if args.cmd == "naics":
            result = lookup_naics(args.code, receipts=args.receipts, employees=args.employees)
            _print_naics(result)
            return 0 if result["ok"] else 1
        ok = True
        if args.uei:
            result = check_uei(args.uei)
            _print_id(result)
            ok = ok and result["ok"]
            print()
        if args.cage:
            result = check_cage(args.cage, ncage=args.ncage)
            _print_id(result)
            ok = ok and result["ok"]
            print()
        if args.naics:
            result = lookup_naics(args.naics, receipts=args.receipts, employees=args.employees)
            _print_naics(result)
            ok = ok and result["ok"]
        if not args.uei and not args.cage and not args.naics:
            print("Give --uei, --cage, and/or --naics.", file=sys.stderr)
            return 2
        return 0 if ok else 1
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
