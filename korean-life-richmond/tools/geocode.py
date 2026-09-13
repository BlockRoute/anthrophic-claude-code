import json, re, pyarrow.parquet as pq, shapely, collections
ABBR={'st':'street','rd':'road','ave':'avenue','blvd':'boulevard','tpke':'turnpike','pkwy':'parkway','dr':'drive','ln':'lane','ct':'court','cir':'circle','hwy':'highway','pl':'place','ter':'terrace','w':'west','e':'east','n':'north','s':'south','mt':'mount'}
def norm(s):
    s=s.lower().replace('.','').replace(',',' ').replace('-',' ')
    s=re.sub(r'\bste\b.*$','',s); s=re.sub(r'\bsuite\b.*$','',s)
    toks=[ABBR.get(t,t) for t in s.split()]
    return ' '.join(toks)
t=pq.read_table('ovt/address.parquet', columns=['postcode','street','number','geometry'])
streets=t.column('street').to_pylist(); nums=t.column('number').to_pylist(); pcs=t.column('postcode').to_pylist(); geoms=t.column('geometry').to_pylist()
idx=collections.defaultdict(list)
for i,(s,n) in enumerate(zip(streets,nums)):
    if s and n: idx[norm(s)].append(i)
places=json.load(open('data/places.json'))
def lookup(addr, zipc):
    m=re.match(r'(\d+)\s+(.*)',addr); num=int(m.group(1)); street=norm(m.group(2))
    cands=idx.get(street,[])
    exact=[i for i in cands if nums[i].isdigit() and int(nums[i])==num and (not zipc or pcs[i]==zipc)]
    if not exact: exact=[i for i in cands if nums[i].isdigit() and int(nums[i])==num]
    if exact:
        i=exact[0]; p=shapely.from_wkb(geoms[i]); return p.x,p.y,'exact',pcs[i]
    # nearest number on same street & zip
    same=[i for i in cands if nums[i].isdigit() and (not zipc or pcs[i]==zipc)]
    if not same: same=[i for i in cands if nums[i].isdigit()]
    if same:
        i=min(same,key=lambda i:abs(int(nums[i])-num)); p=shapely.from_wkb(geoms[i]); return p.x,p.y,f'nearest#{nums[i]}',pcs[i]
    return None,None,'MISS',None
out=[]
for p in places:
    x,y,how,pc=lookup(p['address'],p['zip'])
    p['lon'],p['lat'],p['geo']=x,y,how
    print(f"{p['id']:12} {p['address']:28} {p['zip']}  -> {how:14} {pc}  {y},{x}")
json.dump(places,open('data/places_geo.json','w'),ensure_ascii=False,indent=1)
