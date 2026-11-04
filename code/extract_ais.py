"""Extract a real AIS slice (NOAA MarineCadistre, 2023-01-01) for the Upper NY Bay.
Streams the 877MB CSV once, keeps rows in a tight bbox with valid position/course,
writes a compact CSV for the E20 real-data pipeline."""
import zipfile, csv, io, sys
BBOX = (40.58, 40.72, -74.10, -73.97)   # lat0,lat1,lon0,lon1 -- Upper New York Bay / The Narrows / anchorage
SRC = '../data/ais/AIS_2023_01_01.zip'
OUT = '../data/ais/nybay_slice.csv'
KEEP = ['MMSI','BaseDateTime','LAT','LON','SOG','COG','Heading','VesselName',
        'VesselType','Status','Length','Width','Draft']
def main():
    z = zipfile.ZipFile(SRC)
    n_in = n_keep = 0
    with z.open('AIS_2023_01_01.csv') as f, open(OUT,'w',newline='') as g:
        rdr = csv.reader(io.TextIOWrapper(f,'utf-8'))
        hdr = next(rdr)
        ix = {k: hdr.index(k) for k in KEEP}
        iLat,iLon = ix['LAT'],ix['LON']
        w = csv.writer(g); w.writerow(KEEP)
        la0,la1,lo0,lo1 = BBOX
        for r in rdr:
            n_in += 1
            try:
                lat=float(r[iLat]); lon=float(r[iLon])
            except (ValueError, IndexError):
                continue
            if la0<=lat<=la1 and lo0<=lon<=lo1:
                w.writerow([r[ix[k]] for k in KEEP]); n_keep += 1
            if n_in % 2_000_000 == 0:
                print(f"  scanned {n_in:,} rows, kept {n_keep:,}", flush=True)
    print(f"DONE scanned {n_in:,} kept {n_keep:,} -> {OUT}", flush=True)
if __name__=='__main__':
    main()
