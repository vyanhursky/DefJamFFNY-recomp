"""Exact HD counterpart of the original portrait quad fitting policy."""
from PIL import Image,ImageOps
from fighter_resource_files import require


def hd_tiles(picture,rows,width,height,crops,scale):
    xs=sorted({v for b in crops.values() for v in (b[0],b[2])});ys=sorted({v for b in crops.values() for v in (b[1],b[3])})
    candidates=[]
    for left in xs:
        for right in xs:
            for top in ys:
                for bottom in ys:
                    area=(right-left)*(bottom-top)
                    if right<=left or bottom<=top:continue
                    covered=sum(max(0,min(right,b[2])-max(left,b[0]))*max(0,min(bottom,b[3])-max(top,b[1])) for b in crops.values())
                    if covered==area:candidates.append((area,left,top,right,bottom))
    require(candidates,'UI layout has no full rectangle')
    _,left,top,right,bottom=max(candidates)
    fitted=ImageOps.contain(picture,((right-left)*scale,(bottom-top)*scale),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(width*scale,height*scale))
    canvas.paste(fitted,(left*scale+((right-left)*scale-fitted.width)//2,top*scale+((bottom-top)*scale-fitted.height)//2))
    if picture.width%width==0 and picture.height%height==0 and picture.width//width==picture.height//height in (1,2,4):
        canvas=picture.resize((width*scale,height*scale),Image.Resampling.LANCZOS)
    result={}
    for key,row in rows.items():
        tile=row['image'];out=Image.new('RGBA',(tile['width']*scale,tile['height']*scale))
        out.paste(canvas.crop(tuple(v*scale for v in crops[key])),(0,0));result[tile['name']]=out
    return result
