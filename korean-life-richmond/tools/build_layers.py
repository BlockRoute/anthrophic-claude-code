import json, math, collections, pyarrow.parquet as pq, shapely
from shapely.ops import linemerge, unary_union
W,E,S,N=-77.86,-77.14,37.15,37.80
LAT0=(S+N)/2; K=6000; CX=math.cos(math.radians(LAT0))
def prj(lon,lat): return ((lon-W)*CX*K,(N-lat)*K)
WIDTH,HEIGHT=prj(E,S)
def fmt(v): 
    s=f"{v:.1f}"; return s[:-2] if s.endswith('.0') else s
def path_of_lines(lines):
    out=[]
    for ln in lines:
        cs=list(ln.coords)
        if len(cs)<2: continue
        out.append('M'+' '.join(f"{fmt(x)} {fmt(y)}" for x,y in cs))
    return ''.join(out)
def path_of_polys(polys):
    out=[]
    for pg in polys:
        for ring in [pg.exterior,*pg.interiors]:
            cs=list(ring.coords)
            out.append('M'+' '.join(f"{fmt(x)} {fmt(y)}" for x,y in cs)+'Z')
    return ''.join(out)
def to_prj(g):
    return shapely.transform(g, lambda a: __import__('numpy').column_stack(prj(a[:,0],a[:,1])))
import numpy as np
def prjnp(a): 
    x=(a[:,0]-W)*CX*K; y=(N-a[:,1])*K; return np.column_stack([x,y])
def P(g): return shapely.transform(g, prjnp)
clip=shapely.box(W,S,E,N)
out={'w':round(WIDTH,1),'h':round(HEIGHT,1),'bbox':[W,S,E,N],'k':K,'cx':CX}
# ---- roads
seg=pq.read_table('ovt/segment.parquet', columns=['class','subclass','names','routes','geometry']).to_pylist()
tol={'motorway':0.00004,'trunk':0.00004,'primary':0.00005,'secondary':0.00006,'tertiary':0.00008}
groups=collections.defaultdict(list)
byname=collections.defaultdict(list); byref=collections.defaultdict(list)
for r in seg:
    g=shapely.from_wkb(r['geometry'])
    if not g.intersects(clip): continue
    g=g.intersection(clip)
    cls=r['class']; key=cls+('_link' if r['subclass']=='link' else '')
    gs=g.simplify(tol[cls],preserve_topology=False)
    lines=[gs] if gs.geom_type=='LineString' else [x for x in getattr(gs,'geoms',[]) if x.geom_type=='LineString']
    groups[key].extend(P(l) for l in lines)
    if r['subclass']!='link':
        nm=(r['names'] or {}).get('primary')
        if nm: byname[nm].extend(lines)
        for rt in (r['routes'] or []):
            if rt.get('network') in ('US:I','US:US','US:VA') and rt.get('ref'):
                byref[(rt['network'],rt['ref'])].extend(lines)
out['roads']={k:path_of_lines(v) for k,v in groups.items()}
print({k:len(v) for k,v in out['roads'].items()})
# ---- labels along lines
def anchors(lines, spacing_km, margin_km=1.5, maxn=6, mind=180):
    merged=linemerge(unary_union(lines)) if lines else None
    if merged is None: return []
    parts=[merged] if merged.geom_type=='LineString' else list(merged.geoms)
    res=[]
    for ln in sorted(parts,key=lambda l:-l.length):
        L=ln.length*111.0*0.85  # approx km (mixed), fine for spacing
        if L<margin_km*2: continue
        n=max(1,int(L//spacing_km)); n=min(n,maxn)
        for i in range(n):
            f=(i+0.5)/n
            pt=ln.interpolate(f,normalized=True); p2=ln.interpolate(min(f+0.01,1),normalized=True); p1=ln.interpolate(max(f-0.01,0),normalized=True)
            x,y=prj(pt.x,pt.y); x1,y1=prj(p1.x,p1.y); x2,y2=prj(p2.x,p2.y)
            ang=math.degrees(math.atan2(y2-y1,x2-x1))
            if ang>90: ang-=180
            if ang<-90: ang+=180
            if any(math.hypot(x-r[0],y-r[1])<mind for r in res): continue
            res.append([round(x,1),round(y,1),round(ang,1)])
    return res
shields=[('US:I','95',13),('US:I','64',13),('US:I','295',13),('US:I','195',6),('US:I','85',14),('US:VA','288',12),('US:VA','150',7),('US:VA','76',7),('US:VA','895',9),('US:US','1',12),('US:US','60',12),('US:US','360',12),('US:US','250',12),('US:US','301',14),('US:US','33',14),('US:US','460',14),('US:VA','10',14),('US:VA','147',10),('US:VA','6',14)]
out['shields']=[]
for net,ref,sp in shields:
    for a in anchors(byref.get((net,ref),[]),sp,mind=260):
        out['shields'].append({'n':net.split(':')[1],'r':ref,'x':a[0],'y':a[1],'a':a[2]})
names=['West Broad Street','Hull Street Road','Midlothian Turnpike','Patterson Avenue','Three Chopt Road','Staples Mill Road','Brook Road','Chamberlayne Road','Mechanicsville Turnpike','Nuckols Road','Robious Road','Forest Hill Avenue','Chippenham Parkway','Powhite Parkway','Broad Rock Boulevard','Iron Bridge Road','Courthouse Road','Hopkins Road','North Parham Road','East Parham Road','Monument Avenue','River Road','Genito Road','Pouncey Tract Road','Richmond Highway','Jefferson Davis Highway','Broad Street Road','West Hundred Road','Cox Road','Gaskins Road','Ridgefield Parkway','Huguenot Road','West Huguenot Road','Walmsley Boulevard','Jahnke Road','Grove Avenue','Nine Mile Road','Williamsburg Road','Atlee Road','Meadowbridge Road','Bell Creek Road','Woodman Road','Lauderdale Drive','Old Hundred Road','Charter Colony Parkway','Brandermill Parkway','Quioccasin Road','Skipwith Road','Libbie Avenue','Boulevard','Hermitage Road','Laburnum Avenue','West Laburnum Avenue','East Laburnum Avenue','Wyndham Forest Drive','Shady Grove Road','Mountain Road','Hungary Road','Church Road','Elkhardt Road','Belt Boulevard','East Belt Boulevard','Route 1','Cold Harbor Road','East City Point Road','West City Point Road','South Crater Road','Boydton Plank Road','Washington Street','East Washington Street']
out['roadlabels']=[]
for nm in names:
    for a in anchors(byname.get(nm,[]),7,2.0,4,mind=320):
        out['roadlabels'].append({'t':nm,'x':a[0],'y':a[1],'a':a[2]})
print('shields',len(out['shields']),'roadlabels',len(out['roadlabels']))
# ---- water
wt=pq.read_table('ovt/water.parquet', columns=['subtype','class','names','geometry']).to_pylist()
polys=[]; rivers=[]; wlabels=[]
for r in wt:
    g=shapely.from_wkb(r['geometry'])
    if not g.intersects(clip): continue
    g=g.intersection(clip)
    st=r['subtype']; nm=(r['names'] or {}).get('primary')
    if g.geom_type in ('Polygon','MultiPolygon'):
        if st in ('river','lake','reservoir','water','pond','canal') and r['class'] not in ('swimming_pool','wastewater','basin'):
            gs=g.simplify(0.00006)
            for pg in ([gs] if gs.geom_type=='Polygon' else list(getattr(gs,'geoms',[]))):
                if pg.geom_type=='Polygon' and pg.area*(111e3*CX)*(111e3)>=40000 : polys.append(P(pg))
    elif g.geom_type in ('LineString','MultiLineString'):
        if st=='river' or (nm in ('Swift Creek','Chickahominy River','Tuckahoe Creek','Powhite Creek','Falling Creek','Appomattox River')):
            gs=g.simplify(0.0001)
            rivers.extend(P(l) for l in ([gs] if gs.geom_type=='LineString' else list(gs.geoms)))
out['water']=path_of_polys(polys); out['rivers']=path_of_lines(rivers)
print('water polys',len(polys),'river lines',len(rivers))
# ---- parks
lu=pq.read_table('ovt/land_use.parquet', columns=['subtype','class','names','geometry']).to_pylist()
parks=[]
for r in lu:
    if r['subtype'] not in ('park','protected'): continue
    g=shapely.from_wkb(r['geometry'])
    if not g.intersects(clip): continue
    g=g.intersection(clip).simplify(0.0001)
    for pg in ([g] if g.geom_type=='Polygon' else list(getattr(g,'geoms',[]))):
        if pg.geom_type=='Polygon' and pg.area*(111e3*CX)*(111e3)>=150000: parks.append(P(pg))
out['parks']=path_of_polys(parks); print('parks',len(parks))
# ---- counties (one shape per county so each can be toggled)
da=pq.read_table('ovt/division_area.parquet', columns=['subtype','names','geometry']).to_pylist()
cshapes=[]; clabels=[]
for r in da:
    if r['subtype']!='county': continue
    g=shapely.from_wkb(r['geometry'])
    if not g.intersects(clip): continue
    nm=(r['names'] or {}).get('primary')
    gc=g.intersection(clip)
    if gc.area/g.area<0.2: continue   # skip slivers at the map edge
    gs=gc.simplify(0.0002)
    polys=[P(pg) for pg in ([gs] if gs.geom_type=='Polygon' else list(getattr(gs,'geoms',[]))) if pg.geom_type=='Polygon']
    c=gc.representative_point(); x,y=prj(c.x,c.y)
    minx,miny,maxx,maxy=gc.bounds; bx1,by1=prj(minx,maxy); bx2,by2=prj(maxx,miny)
    short=nm.replace(' County','')
    cshapes.append({'t':short,'full':nm if 'County' in nm else nm+' (city)','d':path_of_polys(polys),'x':round(x,1),'y':round(y,1),'b':[round(bx1,1),round(by1,1),round(bx2,1),round(by2,1)]})
    if short!='Richmond': clabels.append({'t':short.upper(),'x':round(x,1),'y':round(y,1)})
order=['Richmond','Henrico','Chesterfield','Hanover','Goochland','Powhatan','New Kent','Charles City','Colonial Heights','Petersburg','Hopewell','Prince George']
cshapes.sort(key=lambda c: order.index(c['t']) if c['t'] in order else 99)
out['countyshapes']=cshapes; out['countylabels']=clabels
print('counties',[c['t'] for c in cshapes])
# ---- area-of-interest boundaries for the area presets
from shapely.ops import unary_union
def rbox(w,e,s,n,r=0.006): return shapely.box(w,s,e,n).buffer(-r).buffer(r)
county={}
for r in da:
    if r['subtype']=='county': county[(r['names'] or {}).get('primary').replace(' County','')]=shapely.from_wkb(r['geometry'])
wt_all=pq.read_table('ovt/water.parquet', columns=['subtype','names','geometry']).to_pylist()
_riv=[shapely.from_wkb(r['geometry']) for r in wt_all if r['subtype']=='river']
_riv=[g for g in _riv if g.geom_type in ('Polygon','MultiPolygon') and g.area*111*111*0.79>0.3]
james=unary_union(_riv)
james=unary_union([p for p in (james.geoms if hasattr(james,'geoms') else [james]) if p.intersects(shapely.box(-77.75,37.5,-77.3,37.62)) and p.area*111*111*0.79>0.5])
from shapely.ops import nearest_points
def _split(g, want_south):
    parts=g.difference(james.buffer(0.0004))
    parts=[p for p in (parts.geoms if hasattr(parts,'geoms') else [parts]) if p.area>1e-6]
    keep=[]
    for p in parts:
        rp=nearest_points(james, p.representative_point())[0]
        south=p.representative_point().y < rp.y
        if south==want_south: keep.append(p)
    return unary_union(keep) if keep else g
def south_of_james(g): return _split(g, True)
def north_of_james(g): return _split(g, False)
wbroad=unary_union(byname.get('West Broad Street',[]))
wbroad=wbroad.intersection(shapely.box(-77.585,37.55,-77.495,37.66))
areas={
 'West Broad': wbroad.buffer(0.011).buffer(-0.003),
 'Short Pump': county['Henrico'].intersection(rbox(-77.668,-77.575,37.630,37.682)),
 'Downtown': north_of_james(county['Richmond'].intersection(rbox(-77.453,-77.417,37.527,37.549,0.004))),
 'Midlothian': county['Chesterfield'].intersection(rbox(-77.725,-77.560,37.420,37.565)),
 'Southside': south_of_james(county['Richmond']),
 'Mechanicsville': county['Hanover'].intersection(rbox(-77.455,-77.300,37.565,37.668)),
 'Tri-Cities': unary_union([county[k] for k in ('Petersburg','Colonial Heights','Hopewell')]).buffer(0.0005).buffer(-0.0005),
}
out['areashapes']=[]
print('james bounds',james.bounds)
for name,g in areas.items():
    g=g.simplify(0.00025)
    if g.is_empty: print('EMPTY',name); continue
    polys=[P(pg) for pg in ([g] if g.geom_type=='Polygon' else list(getattr(g,'geoms',[]))) if pg.geom_type=='Polygon' and pg.area*111*111*0.79>0.05]
    minx,miny,maxx,maxy=g.bounds; bx1,by1=prj(minx,maxy); bx2,by2=prj(maxx,miny)
    x,y=(bx1+bx2)/2,by1
    out['areashapes'].append({'t':name,'d':path_of_polys(polys),'x':round(x,1),'y':round(y,1),'b':[round(bx1,1),round(by1,1),round(bx2,1),round(by2,1)]})
    print('area',name,round(g.area*111*111*0.79,1),'km2',len(polys))
# ---- localities
dv=pq.read_table('ovt/division.parquet', columns=['subtype','class','names','population','geometry']).to_pylist()
keep={'Midlothian','Ashland','Manakin-Sabot','Brandermill','Chesterfield','Colonial Heights','Petersburg','Sandston','Bon Air','Innsbrook','Short Pump','Glen Allen','Mechanicsville','Chester','Hopewell','Tuckahoe','Lakeside','Highland Springs','Laurel','Wyndham','Woodlake','Meadowbrook','Manchester','Chamberlayne','Enon','Bellwood','Montrose','Dumbarton','Rockwood','Bensley','Varina','Moseley','Rockville','Elmont','Prince George','Ettrick'}
locs=[]
for r in dv:
    if r['subtype']!='locality': continue
    nm=(r['names'] or {}).get('primary'); pop=r['population'] or 0
    if nm in keep or pop>=5000:
        g=shapely.from_wkb(r['geometry']); x,y=prj(g.x,g.y)
        if 0<=x<=WIDTH and 0<=y<=HEIGHT:
            locs.append({'t':nm,'x':round(x,1),'y':round(y,1),'c':r['class'],'p':pop})
out['localities']=locs; print('localities',[l['t'] for l in locs])
json.dump(out,open('data/layers.json','w'))
import os; print('size',os.path.getsize('data/layers.json'))
print({k:len(v) for k,v in out['roads'].items()}, len(out['water']), len(out['parks']))
