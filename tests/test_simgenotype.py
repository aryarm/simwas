from pathlib import Path

import pytest
from click.testing import CliRunner

from haptools.data import Data
from haptools.__main__ import main


# @pytest.mark.skip(reason="this test takes a long time (~2 mins) to run")
def test_basic(capfd):
    tmp_dir = Path("test-dir")
    tmp_dir.mkdir(exist_ok=True)
    prefix = tmp_dir / "simgts"

    cmd = " ".join(
        [
            "simgenotype",
            "--model tests/data/outvcf_gen.dat",
            "--mapdir tests/data/map/",
            "--chroms 1,2",
            "--ref_vcf tests/data/outvcf_test.vcf",
            "--sample_info tests/data/outvcf_info.tab",
            "--pop_field",
            "--verbosity DEBUG",
            f"--out {prefix}.vcf.gz",
        ]
    )
    runner = CliRunner()
    result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
    captured = capfd.readouterr()
    assert result.exit_code == 0
    assert prefix.with_suffix(".bp").exists()
    assert prefix.with_suffix(".vcf.gz").exists()

    # delete the files and directory we just created
    prefix.with_suffix(".bp").unlink()
    prefix.with_suffix(".vcf.gz").unlink()
    tmp_dir.rmdir()
