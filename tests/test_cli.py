"""The console entry point reports expected failures without a traceback."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mirage import cli


def arguments(source, output):
    return ['-i', str(source), '-o', str(output), '--lthr', '8', '--fthr', '0']


def test_console_reports_a_missing_raster_in_one_line(tmp_path, capsys):
    missing = tmp_path/'absent.tif'
    assert cli.console(arguments(missing, tmp_path/'out')) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith('mirage: error: ')
    assert 'Traceback' not in captured.err and captured.out == ''
    assert not (tmp_path/'out').exists()


def test_console_refuses_a_used_output_folder_and_main_still_raises(tmp_path, capsys):
    source = tmp_path/'line.tif'
    values = np.zeros((96, 96), dtype='uint8')
    values[46:50, 18:78] = 255
    with rasterio.open(source, 'w', driver='GTiff', height=96, width=96, count=1, dtype='uint8',
                       crs='EPSG:32718', transform=from_origin(300000, 8900000, 10, 10)) as dataset:
        dataset.write(values, 1)
    output = tmp_path/'out'
    assert cli.console(arguments(source, output)) == 0
    assert '"lineaments"' in capsys.readouterr().out
    assert cli.console(arguments(source, output)) == 1
    assert 'empty output folder' in capsys.readouterr().err
    with pytest.raises(FileExistsError):
        cli.main(arguments(source, output))
