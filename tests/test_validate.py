from pathlib import Path

from click.testing import CliRunner

from haptools.__main__ import main
from haptools.validate import is_hapfile_valid

PARENT_DATADIR = Path(__file__).parent.joinpath("data")
DATADIR = Path(__file__).parent.joinpath("data") / "validate"


def test_generated_haplotypes():
    """
    Tests the dummy .hap generated by the haptools test suite
    """
    hapfile = Path(PARENT_DATADIR / "simple.hap")
    pvarfile = Path(PARENT_DATADIR / "simple.pvar")

    assert is_hapfile_valid(hapfile, pvar=pvarfile)


def test_with_empty_lines():
    """
    Tests a .hap with empty lines
    """
    assert not is_hapfile_valid(DATADIR / "empty_lines.hap")


def test_with_out_of_header_metas_sorted():
    """
    Test a sorted .hap with meta lines out of the header
    """
    assert is_hapfile_valid(DATADIR / "out_of_header_metas.hap", sorted=True)


def test_with_out_of_header_metas_unsorted():
    """
    Test an unsorted .hap with meta lines out of the header
    """
    assert is_hapfile_valid(DATADIR / "out_of_header_metas.hap", sorted=False)


def test_with_10_extras_reordered():
    """
    Tests a .hap file with 10 extra columns
    """
    assert is_hapfile_valid(DATADIR / "10_extras_reordered.hap")


def test_with_unexistent_reorders():
    """
    Tests a .hap with an order[H|R|V] which mentions a non-existent extra column
    """
    assert not is_hapfile_valid(DATADIR / "unexistent_reorders.hap")


def test_with_unexistent_fields():
    """
    Tests a .hap with a data line that is not an H, R or V
    """
    assert not is_hapfile_valid(DATADIR / "unexistent_fields.hap")


def test_with_inadequate_version():
    """
    Tests a .hap with an incorrectly formatted version
    """
    assert not is_hapfile_valid(DATADIR / "inadequate_version.hap")


def test_with_no_version():
    """
    Tests a .hap with no present version
    """
    assert not is_hapfile_valid(DATADIR / "no_version.hap")


def test_with_multiple_versions():
    """
    Tests a .hap with several versions present
    """
    assert not is_hapfile_valid(DATADIR / "multiple_versions.hap")


def test_with_inadequate_version_columns():
    """
    Tests a .hap with a version column of only 2 fields
    """
    assert not is_hapfile_valid(DATADIR / "inadequate_version_columns.hap")


def test_with_invalid_column_addition_column_count():
    """
    Tests a .hap with an extra column declaration of invalid column count
    """
    assert not is_hapfile_valid(DATADIR / "invalid_column_addition_column_count.hap")


def test_with_invalid_column_addition_types():
    """
    Tests a .hap with a column addition for a type which is not H, R or V
    """
    assert not is_hapfile_valid(DATADIR / "invalid_column_addition_types.hap")


def test_with_invalid_column_addition_data_types():
    """
    Tests a .hap with a column addition of unrecognized data type (not s, d or .nf)
    """
    assert not is_hapfile_valid(DATADIR / "invalid_column_addition_data_types.hap")


def test_with_insufficient_columns():
    """
    Tests a .hap with insufficient mandatory columns
    """
    assert not is_hapfile_valid(DATADIR / "insufficient_columns.hap")


def test_with_inconvertible_starts():
    """
    Tests a .hap with start positions that can't be converted to integers
    """
    assert not is_hapfile_valid(DATADIR / "inconvertible_starts.hap")


def test_with_inconvertible_ends():
    """
    Tests a .hap with end positions that can't be converted to integers
    """
    assert not is_hapfile_valid(DATADIR / "inconvertible_ends.hap")


def test_with_inconvertible_starts_var():
    """
    Tests a .hap with start positions that can't be converted to integers in variants
    """
    assert not is_hapfile_valid(DATADIR / "inconvertible_starts_var.hap")


def test_with_inconvertible_ends_var():
    """
    Tests a .hap with end positions that can't be converted to integers in variants
    """
    assert not is_hapfile_valid(DATADIR / "inconvertible_ends_var.hap")


def test_start_after_end():
    """
    Tests a .hap with the start position placed after the end position
    """
    assert not is_hapfile_valid(DATADIR / "start_after_end.hap")


def test_is_directory():
    """
    Tests a validation command with a filename that points to a directory
    """
    assert not is_hapfile_valid(DATADIR / "is_directory.hap")


def test_with_variant_id_of_chromosome():
    """
    Tests a .hap with a variant whose ID is the same as a chromosome ID
    """
    assert not is_hapfile_valid(DATADIR / "variant_id_of_chromosome.hap")


def test_with_hrid_of_chromosome():
    """
    Tests a .hap with a haplotype or repeat with the same ID as a chromosome
    """
    assert not is_hapfile_valid(DATADIR / "hrid_of_chromosome.hap")


def test_with_unexistent_col_in_order():
    """
    Tests a .hap with an order[H|R|V] field that references a non-existent extra column name
    """
    assert not is_hapfile_valid(DATADIR / "unexistent_col_in_order.hap")


def test_with_unassociated_haplotype():
    """
    Tests a .hap with a haplotype that does not have at least one matching repeat
    """
    assert not is_hapfile_valid(DATADIR / "unassociated_haplotype.hap")


def test_with_unrecognizable_allele():
    """
    Tests a .hap with a variant whose allele is not G, C, T or A
    """
    assert not is_hapfile_valid(DATADIR / "unrecognizable_allele.hap")


def test_with_duplicate_ids():
    """
    Tests a .hap with duplicate IDs for H and R fields
    """
    assert not is_hapfile_valid(DATADIR / "duplicate_ids.hap")


def test_with_duplicate_vids_per_haplotype():
    """
    Tests a .hap with duplicate IDs for variants with the same haplotype association
    """
    assert not is_hapfile_valid(DATADIR / "duplicate_vids_per_haplotype.hap")


def test_with_excol_of_wrong_type():
    """
    Tests a .hap with a data line which contains an extra column of d data type but receives s
    """
    assert not is_hapfile_valid(DATADIR / "excol_of_wrong_type.hap")


def test_with_multiple_order_defs():
    """
    Tests a .hap with multiple order[H|R|V] of the same type
    """
    assert not is_hapfile_valid(DATADIR / "multiple_order_defs.hap")


def test_with_insufficient_excols_in_reorder():
    """
    Tests a .hap with an order[H|R|V] that does not reference all extra columns
    """
    assert not is_hapfile_valid(DATADIR / "insufficient_excols_in_reorder.hap")


def test_with_variant_inexistent_haplotype_id():
    """
    Tests a .hap with with a variant that references a non-existent haplotype
    """
    assert not is_hapfile_valid(DATADIR / "variant_inexistent_haplotype_id.hap")


def test_with_missing_variant_in_pvar():
    """
    Tests a .hap along with a .pvar file which is missing an ID present in the .hap
    """
    assert not is_hapfile_valid(
        DATADIR / "simple.hap",
        pvar=DATADIR / "basic_missing_ids.pvar",
    )


def test_unreadable_hapfile():
    """
    Passes a non-existent file to the validator
    """
    assert not is_hapfile_valid(Path("NON_EXISTENT_FILENAME.hap"))


def test_leading_trailing_whitespace():
    """
    We should fail if lines have any leading or trailing whitespace
    """
    basic = DATADIR / "basic.hap"
    with open(basic, "r") as basic_file:
        basic_lines = basic_file.readlines()

    temp_basic = DATADIR / "leading_trailing_whitespace.hap"
    lines = (0, 2, 3, 5)

    # test both kinds of whitespace: tabs and spaces
    for space_kind in (" ", "\t"):
        # test leading whitespace
        for line in lines:
            with open(temp_basic, "w") as temp_basic_file:
                new_lines = basic_lines.copy()
                new_lines[line] = space_kind + new_lines[line]
                temp_basic_file.writelines(new_lines)
            assert not is_hapfile_valid(temp_basic)
        # test trailing whitespace
        for line in lines:
            with open(temp_basic, "w") as temp_basic_file:
                new_lines = basic_lines.copy()
                new_lines[line] = new_lines[line][:-1] + space_kind + "\n"
                temp_basic_file.writelines(new_lines)
            assert not is_hapfile_valid(temp_basic)

    # also try adding a space next to a tab
    with open(temp_basic, "w") as temp_basic_file:
        new_lines = basic_lines.copy()
        new_lines[1] = new_lines[1][:2] + " " + new_lines[1][2:]
        temp_basic_file.writelines(new_lines)
    assert not is_hapfile_valid(temp_basic)

    temp_basic.unlink()


def test_basic(capfd):
    hp_file = DATADIR / "basic.hap"

    cmd = f"validate {hp_file}"
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    assert result.exit_code == 0


def test_no_version(capfd):
    hp_file = DATADIR / "no_version.hap"

    cmd = f"validate {hp_file}"
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    assert result.exit_code != 0


def test_no_version(capfd):
    hp_file = DATADIR / "no_version.hap"

    cmd = f"validate {hp_file}"
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    assert result.exit_code != 0


def test_sorted(capfd):
    hp_file = PARENT_DATADIR / "simple.hap"

    cmd = f"validate --sorted {hp_file}"
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    assert result.exit_code == 0


def test_with_pvar(capfd):
    gt_file = PARENT_DATADIR / "simple.pvar"
    hp_file = PARENT_DATADIR / "simple.hap"

    cmd = f"validate --genotypes {gt_file} {hp_file}"
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    assert result.exit_code == 0
