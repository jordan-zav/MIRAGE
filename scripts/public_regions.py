"""Download fixed public GA regions through NCSS and ArcGIS REST, no desktop."""
import hashlib
import json
from pathlib import Path
import sys

import requests

REGIONS = [('Pilbara', 118.0, -22.0, 118.4, -21.6, 32750),
           ('Mount-Isa', 139.3, -20.9, 139.7, -20.5, 32754),
           ('Broken-Hill', 141.2, -32.1, 141.6, -31.7, 32754)]
MAG = 'https://thredds.nci.org.au/thredds/ncss/grid/iv65/Geoscience_Australia_Geophysics_Reference_Data_Collection/national_geophysical_compilations/Magmap2019/Magmap2019-grid-tmi_rtp-AWAGS_MAG_2019.nc'
FAULTS = 'https://services.ga.gov.au/gis/rest/services/GA_Surface_Geology/MapServer/7'


def download(destination):
    destination = Path(destination)
    destination.mkdir(exist_ok=True)
    rows = []
    for name, west, south, east, north, epsg in REGIONS:
        params = dict(var='Band1', west=west, east=east, south=south, north=north, horizStride=1, accept='netcdf', addLatLon='true')
        response = requests.get(MAG, params=params, timeout=180)
        response.raise_for_status()
        grid = destination / f'{name}.nc'
        grid.write_bytes(response.content)
        grid_url = response.url
        params = dict(f='geojson', where='1=1', geometry=f'{west},{south},{east},{north}', geometryType='esriGeometryEnvelope',
                      inSR=4283, outSR=4326, spatialRel='esriSpatialRelIntersects', outFields='*', returnGeometry='true')
        response = requests.get(FAULTS + '/query', params=params, timeout=120)
        response.raise_for_status()
        faults = response.json()
        if 'features' not in faults or not faults['features'] or faults.get('exceededTransferLimit'):
            raise ValueError(f'Incomplete/empty mapped faults for {name}: {str(faults)[:300]}')
        faultfile = destination / f'{name}-faults.geojson'
        faultfile.write_bytes(response.content)
        rows.append(dict(region=name, bounds_wsen=[west, south, east, north], target_epsg=epsg,
                         grid_url=grid_url, grid_file=grid.name, grid_sha256=hashlib.sha256(grid.read_bytes()).hexdigest(),
                         faults_url=response.url, faults_file=faultfile.name, faults_sha256=hashlib.sha256(faultfile.read_bytes()).hexdigest(),
                         fault_features=len(faults['features']), license='CC-BY-4.0',
                         attribution='Commonwealth of Australia (Geoscience Australia), Magnetic Anomaly Map Seventh Edition 2020 and Surface Geology of Australia 1:1M',
                         modifications='NCSS geographical subset and REST fault envelope selection; metric reprojection follows separately'))
        print(name, len(grid.read_bytes()), 'bytes, faults', len(faults['features']), flush=True)
        (destination / 'provenance.json').write_text(json.dumps(rows, indent=2))
    response = requests.get(FAULTS, params={'f': 'pjson'}, timeout=60)
    response.raise_for_status()
    (destination / 'faults-license-metadata.json').write_bytes(response.content)
    response = requests.get(MAG.replace('/ncss/grid/', '/dodsC/') + '.das', timeout=60)
    response.raise_for_status()
    (destination / 'magnetic-metadata.das').write_bytes(response.content)


if __name__ == '__main__':
    download(sys.argv[1])
