#!/usr/bin/env python3
"""Read-only NAS media estate discovery. Never writes to NAS. Brand map from org_brand_aliases."""
import os, sqlite3, json, re, time, sys
BASE='/Users/wolfterminal/beta-os'
OUT=BASE+'/state/nas-estate'
ROOTS=['/Volumes/01-Media-Library','/Volumes/00-Editing-Workspace-3','/Volumes/02-Stock-Assets-1','/Volumes/03-Templates']
SKIP={'#recycle','@eaDir','.Trashes','.Spotlight-V100','.fseventsd','scratch','.TemporaryItems'}
IMG={'.jpg','.jpeg','.png','.heic','.heif','.webp','.tif','.tiff','.dng','.cr2','.cr3','.arw','.nef','.raf','.gif','.bmp','.psd'}
VID={'.mp4','.mov','.m4v','.mxf','.avi','.mts','.m2ts','.mkv','.insv','.lrv','.braw','.r3d','.webm','.3gp'}
AUD={'.wav','.mp3','.m4a','.aac','.aif','.aiff','.flac'}
GFX={'.ai','.eps','.svg','.pdf','.indd','.aep','.prproj','.drp','.fcpxml','.cube','.otf','.ttf'}
def norm(s): return re.sub(r'[\s_\-]+',' ',s.lower()).strip()
db=sqlite3.connect(BASE+'/catalog/content_library.sqlite')
alias={}
for a,bid,slug,label in db.execute('select * from org_brand_aliases'):
    alias[norm(a)]=slug
# folder evidence seen on NAS that is not yet an alias: medium confidence, recorded for review
FOLDER_RULES={'amg atrium':'atrium','uma blu cafe':'umablu','rainforest restaurant':'rainforest','selong selo':'selo','tropic at selong':'tropik','habitat':'habitat'}
def brand_for(parts):
    for p in parts:
        n=norm(p)
        if n in alias: return alias[n],'certain'
    for p in parts:
        n=norm(p)
        if n in FOLDER_RULES: return FOLDER_RULES[n],'folder_rule'
    return 'UNKNOWN','review_required'
agg={}; gaps=[]; n=0; t0=time.time()
man=open(OUT+'/manifest.tsv','w')
for root in ROOTS:
    if not os.access(root,os.R_OK): gaps.append(root+' NOT READABLE'); continue
    for dp,dns,fns in os.walk(root, onerror=lambda e: gaps.append(str(e))):
        dns[:]=[d for d in dns if d not in SKIP and not d.startswith('.')]
        rel=os.path.relpath(dp,root); parts=[] if rel=='.' else rel.split(os.sep)
        for f in fns:
            if f.startswith('.') or f.startswith('._'): continue
            ext=os.path.splitext(f)[1].lower()
            kind='image' if ext in IMG else 'video' if ext in VID else 'audio' if ext in AUD else 'graphic' if ext in GFX else None
            if not kind: continue
            p=os.path.join(dp,f)
            try: st=os.stat(p)
            except Exception as e: gaps.append('STAT '+p+' '+str(e)); continue
            b,conf=brand_for(parts)
            if root.endswith(('02-Stock-Assets-1','03-Templates')) and b=='UNKNOWN': b,conf='SHARED_STOCK','shared'
            k=(b,root.split('/')[-1]); a=agg.setdefault(k,{'files':0,'image':0,'video':0,'other':0,'bytes':0,'conf':{}})
            a['files']+=1; a['bytes']+=st.st_size; a['image' if kind=='image' else 'video' if kind=='video' else 'other']+=1
            a['conf'][conf]=a['conf'].get(conf,0)+1
            man.write('\t'.join([p,f,kind,str(st.st_size),str(int(st.st_mtime)),b,conf,root])+'\n')
            n+=1
            if n%2000==0:
                open(OUT+'/progress.txt','w').write(f'{n} files {time.time()-t0:.0f}s at {dp}\n')
man.close()
res={'finished':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'files':n,'secs':round(time.time()-t0),'gaps':gaps[:200],'gap_count':len(gaps),
     'rows':[{'brand':k[0],'root':k[1],**v} for k,v in sorted(agg.items())]}
json.dump(res,open(OUT+'/discovery.json','w'),indent=1)
open(OUT+'/progress.txt','w').write(f'DONE {n} files {res["secs"]}s\n')
