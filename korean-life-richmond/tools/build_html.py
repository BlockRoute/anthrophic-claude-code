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

# ---- standalone site build (full document, optional Google Analytics tag)
import os
cfg={}
if os.path.exists('data/site.json'): cfg=json.load(open('data/site.json'))
ga=cfg.get('ga4_measurement_id','')
ga_tag=''
if ga and ga.startswith('G-'):
    ga_tag=f"""<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{ga}');</script>
"""
head=f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta property="og:title" content="Korean Life in Richmond">
<meta property="og:description" content="Korean churches, grocery stores, academies and hospitals in and around Richmond, Virginia.">
<meta name="theme-color" content="#0f1319">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%23f2b63f'/%3E%3Ctext x='16' y='21' font-size='15' font-weight='700' text-anchor='middle' font-family='sans-serif' fill='%230f1319'%3E%EB%A7%88%3C/text%3E%3C/svg%3E">
{ga_tag}<style>body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
"""
os.makedirs('out/site',exist_ok=True)
open('out/site/index.html','w').write(head+html+"\n</body>\n</html>\n")
print('site bytes',os.path.getsize('out/site/index.html'),'ga:',ga or '(none yet)')
