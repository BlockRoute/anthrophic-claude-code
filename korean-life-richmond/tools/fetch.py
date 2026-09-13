import time, sys, pyarrow as pa, pyarrow.fs as fs, pyarrow.dataset as ds, pyarrow.compute as pc, pyarrow.parquet as pq
REL="2026-08-19.0"
W,E,S,N=-77.86,-77.14,37.15,37.80
s3=fs.S3FileSystem(anonymous=True, region="us-west-2", proxy_options={'scheme':'http','host':'127.0.0.1','port':int(__import__('os').environ.get('HTTPS_PROXY','http://127.0.0.1:38591').rsplit(':',1)[1])})
def fetch(theme, typ, columns, extra=None, out=None, bbox=(W,E,S,N)):
    t=time.time()
    path=f"overturemaps-us-west-2/release/{REL}/theme={theme}/type={typ}/"
    files=[f.path for f in s3.get_file_info(fs.FileSelector(path)) if f.type==fs.FileType.File]
    d=ds.dataset(files, filesystem=s3, format="parquet")
    w,e,s,n=bbox
    filt=(pc.field('bbox','xmin')>w)&(pc.field('bbox','xmax')<e)&(pc.field('bbox','ymin')>s)&(pc.field('bbox','ymax')<n)
    if extra is not None: filt=filt&extra
    cols=[c for c in columns if c in d.schema.names]
    tbl=d.to_table(filter=filt, columns=cols)
    pq.write_table(tbl, f"{out or typ}.parquet")
    print(f"{theme}/{typ}: {tbl.num_rows} rows, {len(files)} files, {time.time()-t:.0f}s", flush=True)
which=sys.argv[1]
if which=="divisions":
    fetch("divisions","division_area",["id","subtype","class","names","geometry","bbox"], extra=pc.field('subtype').isin(['county','locality']), bbox=(-78.3,-76.7,36.9,38.1))
    fetch("divisions","division",["id","subtype","class","names","population","geometry","bbox"], extra=pc.field('subtype').isin(['locality','county','macrohood']))
elif which=="water":
    fetch("base","water",["id","subtype","class","names","geometry","bbox"])
    fetch("base","land_use",["id","subtype","class","names","geometry","bbox"], extra=pc.field('subtype').isin(['park','protected','recreation','airport','education','medical','military']), out="land_use")
elif which=="roads":
    fetch("transportation","segment",["id","subtype","class","subclass","names","routes","geometry","bbox"], extra=(pc.field('subtype')=='road')&pc.field('class').isin(['motorway','trunk','primary','secondary','tertiary']))
elif which=="places":
    fetch("places","place",["id","names","categories","confidence","websites","phones","addresses","geometry","bbox"])
elif which=="addresses":
    fetch("addresses","address",["id","country","postcode","street","number","unit","address_levels","geometry","bbox"])
