"""CAF v5: borrow a named original fighter's complete motion core."""
import copy
from fighter_resource_files import require
from fighter_registry import fingerprint


def load_recipe(root,value,catalog,game):
    clean=copy.deepcopy(value);key=clean.pop('retail_moveset',None)
    require(type(key) is str and key in catalog.rows,'CAF v5 requires an available original fighter moveset')
    donor=catalog.rows[key];core=donor['native_binding']['core_id']
    require(type(core) is int and 1<=core<=86,'CAF moveset must use an original retail motion core')
    from fighter_caf_face import load_recipe as load_face
    result=load_face(root,clean,catalog,game)
    result.update(core=core,retail_moveset=key,sha256=fingerprint(value))
    mask=donor['fields']['FightingStyle']['word'];primary=catalog.db.word(donor['record_offset']+72)
    require(type(mask) is int and 0<mask<=31,'Unsupported retail fighting-style mask')
    styles=[i for i in range(5) if mask&(1<<i)];first=[i for i in styles if primary&(1<<i)]
    if first:styles=first[:1]+[i for i in styles if i!=first[0]]
    result['retail_styles']=styles
    return result
