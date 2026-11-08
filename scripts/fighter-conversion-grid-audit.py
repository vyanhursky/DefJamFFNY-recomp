"""Account for legacy selector changes without importing source UI code/models.

Verify preserved original actions/constants/drawables, the complete appended
static graph closures, all per-state placements and exact original pixels.
Only the separately compiled typed pixel sources enter an ordinary package.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'setup'))
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_animation import require
from fighter_portrait import UITextures
from fighter_ui_model import UIModel
import fighter_apt as apt


def digest(data):return hashlib.sha256(data).hexdigest()
def site(x):return x-4 if 0x1A0<=x<0x230 or x==0x260 else x
def target(x):return x-4 if 0x1A0<=x<0x230 or 0x260<=x<0x2B8 else x


def closure(source,original,model,image,n):
    base=source.exports[f'__Model:::{model}']-0x378
    old,oldmodel,oldimage={2:(0xF450,2,1),3:(0x2ACC0,4,3),4:(0x2AE10,4,3)}[n]
    require(0<=base and base+0x448<=len(source.parts[1]),'Source grid closure exceeds data')
    exports={f'__Model:::{model}':0x378,f'__BBOX:::{model}':0x230,
             f'__VB:::__GPvb_9_0_{model}':0xA0,f'__RM:::__GP_RM_{model}_0':0x1A0}
    require(all(source.exports.get(k)==base+v for k,v in exports.items()),'Source closure exports differ')
    a=bytearray(source.parts[1][base:base+0x448]);b=bytearray(original.parts[1][old:old+0x448])
    pointers={at-base:row for at,row in source.pointers.items() if base<=at<base+0x448}
    trusted={at-old:row for at,row in original.pointers.items() if old<=at<old+0x448}
    require(len(pointers)==42 and {site(at) for at in pointers}==trusted.keys(),'Source relocation sites differ')
    strings={0x1D0:f'{model}_0_RM = TextureApt',0x260:str(image),0x310:f'ScaleMatrix::{image}::TextureMatrix',0x32C:str(image),0x42C:str(model)}
    def imported(name,image):
        return re.sub(r'UID=[0-9]+;','UID=OWNED;',name).replace(f'SHAPENAME={image},1;','SHAPENAME=OWNED,1;')
    for at,(symbol,destination) in pointers.items():
        a[at:at+4]=bytes(4);mapped=site(at);other,expected=trusted[mapped]
        if at in strings:
            require(destination is not None and source.string(1,destination)==strings[at],'Source live grid identity differs')
        elif destination is None:
            require(expected is None and imported(source.names[symbol],image)==imported(original.names[other],oldimage),'Source grid import controls differ')
        else:require(expected is not None and target(destination-base)==expected-old,'Source grid local graph differs')
    for at in trusted:b[at:at+4]=bytes(4)
    for start,end,dest in [(0,0x188,0),(0x1A0,0x230,0x19C),(0x230,0x258,0x230),(0x260,0x2B8,0x25C),(0x2E0,0x320,0x2E0),(0x324,0x448,0x324)]:
        require(a[start:end]==b[dest:dest+end-start],'Source grid live geometry/material bytes differ')
    for start,end in [(0x188,0x1A0),(0x258,0x260),(0x2B8,0x2E0),(0x320,0x324)]:
        require(not any(dest is not None and base+start<=dest<base+end for _,dest in source.pointers.values()),'Source unused name is referenced')
    require(pointers[0x1E8][0]==pointers[0x334][0] and pointers[0x1E0][0]==pointers[0x30C][0],'Source allocation sharing differs')
    uids=[re.search(r'UID=([0-9]+);',source.names[pointers[at][0]]) for at in (0x1E8,0x1E0)]
    require(all(uids) and uids[0][1]==uids[1][1],'Source allocation family identities differ')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--portraits',type=Path,required=True);parser.add_argument('--game',type=Path,default=ROOT/'game');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();require(not args.out.exists(),'Choose a new grid audit output')
    portraits=json.loads(args.portraits.read_text());selections={r['selection'] for r in portraits['rows'] if r['passed']}
    require(len(selections)==len(portraits['rows'])==46,'Grid audit requires the complete actual added roster')
    data=(args.game/'screens/screens.viv').read_bytes();pins=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
    require(digest(data)==pins['screens_sha256'],'Original screens differ from baseline');baseline=Archive(data);rows=[]
    for n in (2,3,4):
        stem=f'chooseF{n}';path=f'screens/battle/{stem}.big';original=Archive(unpack(baseline.read(path)));source_data=(args.source/path).read_bytes();source=Archive(unpack(source_data))
        require(set(source.by_name)==set(original.by_name),'Source grid has unexpected members')
        require(source.read(stem+'.const')==original.read(stem+'.const'),'Source action constants differ')
        a,b=(movie.read(stem+'.apt') for movie in (original,source));root,constants=apt.parse_const(original.read(stem+'.const'))
        def chars(data):
            count,table=struct.unpack_from('<II',data,root+20);require(count<=9999 and table+4*count<=len(data),'Grid characters escape their envelope')
            return struct.unpack_from('<'+'I'*count,data,table)
        oldchars,newchars=chars(a),chars(b);require(len(newchars)==len(oldchars)+184,'Unexpected source static character count')
        ex=struct.unpack_from('<I',a,8)[0];thumb=[i for o,i in struct.iter_unpack('<II',a[12:12+8*ex]) if apt.read_cstr(a,o)=='thumbAll'];require(len(thumb)==1,'Missing thumbnail sprite')
        sprite=oldchars[thumb[0]];count,frames=struct.unpack_from('<II',a,sprite+8);require(count==300 and struct.unpack_from('<II',b,sprite+8)==(count,frames),'Unexpected source thumbnail timeline shape')
        masked=set(range(root+20,root+28))|set(range(sprite+8,sprite+16))
        changed={frame for k in selections for frame in (k,k+149)}
        for frame in changed:masked.update(range(frames+8*frame,frames+8*frame+8))
        require(len(b)>=len(a) and all(a[i]==b[i] for i in range(len(a)) if i not in masked),'Source changes original menu behavior outside static frame rows')
        olddata,newdata=(movie.read(stem+'.o') for movie in (original,source));oldmodel,newmodel=UIModel(olddata,digest(olddata)),UIModel(newdata,digest(newdata))
        require(newmodel.parts[1][:len(oldmodel.parts[1])]==oldmodel.parts[1] and newmodel.symbols[:len(oldmodel.symbols)]==oldmodel.symbols
                and newmodel.relocations[:len(oldmodel.relocations)]==oldmodel.relocations,'Source modifies an original UI drawable')
        oldtex,newtex=(UITextures(unpack(movie.read(stem+'.xsh'))) for movie in (original,source))
        require(len(newtex.images)==len(oldtex.images)+92,'Unexpected source tile count')
        for image in oldtex.images:require(oldtex.single_image(int(image['name']))==newtex.single_image(int(image['name'])),'Source changes an original tile')
        states=apt.parse_character(b,sprite)['frames'];shapes=set();images=set()
        for frame in sorted(changed):
            items=states[frame];require([kind for kind,_ in items]==['Action','PlaceObject'],'Source custom frame is not static')
            instructions=apt.disassemble_block(b,items[0][1]['instructions_at'],constants,max_bytes=16)
            require([i.name for i in instructions]==['Stop','End'],'Source custom frame contains behavior beyond Stop')
            placement=items[1][1];require(placement['flags'] in (3,6) and placement['depth']==1 and not placement['name']
                and placement['clip_depth']==-1 and not placement['clip_events'] and (placement['matrix'] is None or placement['matrix']==(1.,0.,0.,1.,0.,0.)),'Source placement has unsupported display behavior')
            identity=placement['character'];require(len(oldchars)<=identity<len(newchars),'Source state uses an original shape');shapes.add(identity)
            shape=newchars[identity];require(struct.unpack_from('<II4f',b,shape)==(1,0x09876543,-18.5,-18.5,18.5,18.5),'Source shape bounds differ')
            model_id=struct.unpack_from('<I',b,shape+24)[0];base=newmodel.exports[f'__Model:::{model_id}'];names=newmodel.pointers[base+0xA0][1];image=int(newmodel.string(1,newmodel.pointers[names][1]));images.add(image)
            closure(newmodel,oldmodel,model_id,image,n)
        require(len(shapes)==len(images)==92,'Source states unexpectedly share static drawables')
        rows.append({'path':path,'sha256':digest(source_data),'states':92,'closures':92,'original_actions_constants_and_drawables_preserved':True,'passed':True})
    report={'schema':'fighter-grid-source-audit-1','rows':rows,'states':sum(r['states'] for r in rows),'native_playtest':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as out:out.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
