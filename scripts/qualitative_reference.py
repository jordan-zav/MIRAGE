"""Open Lightning Creek grid: verified download and qualitative curve overlay."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np


URL = 'https://github.com/fatiando-data/lightning-creek-magnetic-grid/releases/download/v1/lightning-creek-magnetic-grid.nc'
SHA256 = 'd83f5d89f82cee128227746e2edab4498d37a3904c4770752135b7972d64629f'


def main(session,cache):
    import xarray as xr
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from mirage import extract
    cache,session = Path(cache),Path(session)
    cache.mkdir(parents=True,exist_ok=True)
    path = cache/'lightning-creek-magnetic-grid.nc'
    if not path.exists():
        with urlopen(URL,timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise ValueError('Public grid digest mismatch')
        with path.open('xb') as handle:
            handle.write(data)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SHA256
    dataset = xr.load_dataset(path)
    variable = next(value for value in dataset.data_vars.values() if value.ndim == 2)
    array = np.asarray(variable.values)
    # Read coordinate directions, then preserve metric native pixels.
    north = np.asarray(dataset[variable.dims[0]])
    east = np.asarray(dataset[variable.dims[1]])
    if north[0] < north[-1]:
        array,north = array[::-1],north[::-1]
    if east[0] > east[-1]:
        array,east = array[:,::-1],east[::-1]
    size = float(abs(east[1]-east[0]))
    assert np.allclose(np.abs(np.diff(north)),size)
    assert np.isfinite(array).all()
    transform = (size,0,float(east[0]-size/2),0,-size,float(north[0]+size/2))
    output = session/'reference'
    output.mkdir(exist_ok=True)
    (output/path.name).write_bytes(path.read_bytes())
    result = extract(array,pixel_size=size,transform=transform,method='worming',heights=(0,100,250))
    fig,axes = plt.subplots(1,2,figsize=(10,5))
    extent = [east[0]-size/2,east[-1]+size/2,north[-1]-size/2,north[0]+size/2]
    axes[0].imshow(array,extent=extent,cmap='RdBu_r')
    axes[0].set_title('Lightning Creek: magnetic anomaly (nT)')
    axes[1].imshow(result.strength,extent=extent,cmap='gray')
    for line in result.lines:
        coords = np.asarray(line.coords)
        axes[1].plot(coords[:,0],coords[:,1],color='red',linewidth=.5)
    axes[1].set_title('Worming curves: qualitative only')
    for axis in axes:
        axis.set(xlabel='Easting (m)',ylabel='Northing (m)')
        axis.xaxis.set_major_locator(MaxNLocator(4))
        axis.yaxis.set_major_locator(MaxNLocator(4))
        axis.ticklabel_format(style='sci',axis='both',scilimits=(0,0),useOffset=False)
    fig.suptitle('Geoscience Australia 2019 / Fatiando a Terra 2022, CC BY 4.0; no structural ground truth')
    fig.tight_layout()
    fig.savefig(output/'lightning-creek-overlay.png',dpi=160)
    record = {'url':URL,'sha256':SHA256,'license':'CC-BY-4.0',
              'attribution':'Geophysical Acquisition & Processing Section 2019, Geoscience Australia, MIM P1029; Fatiando a Terra Developers 2022, Lightning Creek magnetic grid v1',
              'source':'http://pid.geoscience.gov.au/dataset/ga/142419',
              'doi':'https://doi.org/10.5281/zenodo.7079711',
              'license_url':'https://creativecommons.org/licenses/by/4.0/',
              'changes':'Coordinate order normalized to north-up; unresampled grid; MIRAGE continuation/ridge overlay added',
              'shape':list(array.shape),'pixel_size_m':size,'curves':len(result.lines),
              'quantitative_ground_truth':False}
    (output/'provenance.json').write_text(json.dumps(record,indent=2))
    for name in ('README.md','LICENSE.txt'):
        with urlopen('https://raw.githubusercontent.com/fatiando-data/lightning-creek-magnetic-grid/main/'+name,timeout=60) as response:
            (output/('upstream-'+name.replace('.md','.txt'))).write_bytes(response.read())
    print(json.dumps(record,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('cache')
    args = parser.parse_args()
    main(args.session,args.cache)
