import json
L=json.load(open('data/layers.json')); P=json.load(open('data/places_geo.json'))
for p in P:
    for k in ('geo',): p.pop(k,None)
base=[]
base.append(f'<path class="parks" d="{L["parks"]}"/>')
base.append(f'<path class="water" d="{L["water"]}"/>')
base.append(f'<path class="rivers" d="{L["rivers"]}"/>')
base.append(f'<path class="counties" d="{L["counties"]}"/>')
for cls in ['tertiary','secondary','primary','trunk','motorway']:
    base.append(f'<path class="road r-{cls}" d="{L["roads"].get(cls,"")}"/>')
links=''.join(L['roads'].get(k,'') for k in ['tertiary_link','secondary_link','primary_link','trunk_link','motorway_link'])
base.append(f'<path class="road r-link" d="{links}"/>')
Lj={k:L[k] for k in ('w','h','bbox','k','cx','shields','roadlabels','countylabels','localities')}
html=open('template.html').read().replace('__BASE__',''.join(base)).replace('__LAYERS__',json.dumps(Lj,ensure_ascii=False)).replace('__PLACES__',json.dumps(P,ensure_ascii=False))
open('out/index.html','w').write(html)
import os; print('bytes',os.path.getsize('out/index.html'))
