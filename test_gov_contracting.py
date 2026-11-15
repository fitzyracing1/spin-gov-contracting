from gov_contracting import (
    INTRO,
    SAMPLE_DISCLAIMER,
    check_cage,
    check_uei,
    load_sample_naics,
    lookup_naics,
    main,
)


def test_intro_names_the_project_and_sponsor():
    assert "spin-gov-contracting" in INTRO
    assert "Joshua Almeida" in INTRO
    assert "https://github.com/sponsors/fitzyracing1" in INTRO


def test_help_is_zero():
    assert main([]) == 0
    assert main(["--help"]) == 0


def test_uei_accepts_well_shaped_value():
    # Made-up value used only to test shape. Not a real entity.
    result = check_uei("J6H4FB3N5YK4")
    assert result["ok"] is True
    assert result["value"] == "J6H4FB3N5YK4"


def test_uei_rejects_letter_o_and_leading_zero_and_length():
    assert check_uei("J6H4FB3N5YKO")["ok"] is False
    assert check_uei("06H4FB3N5YK4")["ok"] is False
    assert check_uei("J6H4FB3N5YK")["ok"] is False
    assert check_uei("J6H4-FB3N5YK4")["ok"] is False


def test_uei_normalizes_case():
    assert check_uei("j6h4fb3n5yk4")["ok"] is True


def test_cage_accepts_dla_format_examples():
    # Format examples published by DLA QPD help: 0YWL3, 3Y633, 00N34, 20999.
    for value in ("0YWL3", "3Y633", "00N34", "20999"):
        assert check_cage(value)["ok"] is True, value


def test_cage_rejects_i_o_and_non_digit_last():
    assert check_cage("1IAO2")["ok"] is False
    assert check_cage("1AA")["ok"] is False
    assert check_cage("1AAAB")["ok"] is False


def test_ncage_flag_allows_letter_in_last_position():
    made_up = "A1B2C"
    assert check_cage(made_up)["ok"] is False
    assert check_cage(made_up, ncage=True)["ok"] is True


def test_sample_table_is_clearly_sample_and_loads():
    table = load_sample_naics()
    assert "541511" in table
    assert table["541511"]["title"].startswith("Sample")
    assert "SAMPLE" in SAMPLE_DISCLAIMER
    assert "not official" in SAMPLE_DISCLAIMER.lower()


def test_naics_sample_comparison():
    under = lookup_naics("541511", receipts="5000000")
    assert under["row"]["title"].startswith("Sample")
    assert "under" in under["comparison"]
    over = lookup_naics("541511", receipts="20000000")
    assert "over" in over["comparison"]
    employees = lookup_naics("236220", employees="40")
    assert "under" in employees["comparison"]


def test_naics_not_in_sample_table_is_not_a_format_error():
    result = lookup_naics("999999")
    assert result["ok"] is True
    assert result["missing"] is True


def test_bad_naics_format():
    result = lookup_naics("54")
    assert result["ok"] is False
    assert main(["naics", "54"]) == 1


def test_cli_uei_and_cage(capsys):
    assert main(["uei", "J6H4FB3N5YK4"]) == 0
    assert "ok" in capsys.readouterr().out
    assert main(["cage", "0YWL3"]) == 0
    assert main(["uei", "06H4FB3N5YK4"]) == 1


def test_cli_naics_disclaimer(capsys):
    assert main(["naics", "541511", "--receipts", "5000000"]) == 0
    out = capsys.readouterr().out
    assert "SAMPLE" in out
    assert "not official" in out.lower()
    assert "under" in out


def test_cli_check(capsys):
    assert main(["check", "--uei", "J6H4FB3N5YK4", "--cage", "0YWL3", "--naics", "541511"]) == 0
    out = capsys.readouterr().out
    assert "UEI" in out and "CAGE" in out and "NAICS" in out
