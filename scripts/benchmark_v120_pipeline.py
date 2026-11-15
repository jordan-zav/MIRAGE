"""Measure the unchanged v1.2 file pipeline, separately from array-route timing."""
import argparse
import json
from pathlib import Path
import time

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin

from benchmark_lineaments import score
from mirage.engine import Result
from mirage.pipeline import run_extraction_job


def main(session):
    session = Path(session)
    bank = session/'bank'
    records = json.loads((bank/'manifest.json').read_text())['records']
    output = session/'v120-pipeline-benchmark'
    output.mkdir(exist_ok=False)
    inputs = output/'inputs'
    inputs.mkdir()
    for record in records:
        if record['split'] == 'train':
            continue
        image = np.load(bank/record['file'])['image'].astype('float32')
        with rasterio.open(inputs/f"{record['id']}.tif",'w',driver='GTiff',height=image.shape[0],
                           width=image.shape[1],count=1,dtype='float32',crs='EPSG:32618',
                           transform=from_origin(0,image.shape[0]*25,25,25)) as dataset:
            dataset.write(image,1)

    def execute(record,gthr):
        folder = output/f"gthr{gthr}-case{record['id']}"
        started = time.perf_counter()
        summary = run_extraction_job(geotiff=inputs/f"{record['id']}.tif",out_dir=folder,
                                      radi=1,gthr=gthr,lthr=4,fthr=0,athr=20,dthr=3,
                                      extraction_mode='geophysics',geophys_filters='TDR',
                                      geophys_extract_type='trough',workers=1)
        frame = gpd.read_file(summary['outputs']['geopackage'])
        attributes = []
        for line in frame.geometry:
            dx,dy = np.subtract(line.coords[-1],line.coords[0])
            attributes.append({'azimuth':float(np.degrees(np.arctan2(dx,dy)) % 180)})
        result = Result(list(frame.geometry),attributes,np.zeros((64,64)))
        elapsed = time.perf_counter()-started
        data = np.load(bank/record['file'])
        return {'method':'A_v120_file_pipeline','case':record['id'],'seconds':elapsed,
                **score(result,data['truth'],data['azimuth'])}
    candidates = []
    for threshold in (10,20,35,50):
        rows = [execute(record,threshold) for record in records if record['split']=='validation']
        candidates.append((float(np.mean([row['f1'] for row in rows])),threshold))
    _,chosen = max(candidates,key=lambda pair:pair[0])
    testing = [execute(record,chosen) for record in records if record['split']=='test']
    summary = {key:float(np.mean([row[key] for row in testing if row[key] is not None]))
               for key in testing[0] if key not in ('method','case') and any(row[key] is not None for row in testing)}
    record = {'thresholds_validation':candidates,'chosen_gthr':chosen,
              'timing_scope':'Full file pipeline including raster/vector/report I/O; not directly comparable to array-only timings',
              'numerical_engine':'mirage.line_core and pipeline; normalized source equal to v1.2.0',
              'summary':summary,'test':testing}
    (output/'metrics.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    main(parser.parse_args().session)
