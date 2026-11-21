from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
F="/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
K=4; W=1024*K
def hx(h,a=255): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))+(a,)
CREAM=hx('FFF9F0'); INK=hx('292D32'); COP=hx('A95632'); FOLD=hx('E9DFCC')
def s(v): return int(v*K)
def text(d,cx,cy,t,size,col):
    fn=ImageFont.truetype(F,s(size)); b=d.textbbox((0,0),t,font=fn); d.text((s(cx)-(b[2]-b[0])/2-b[0],s(cy)-(b[3]-b[1])/2-b[1]),t,font=fn,fill=col)
def icon(doc=False):
    im=Image.new("RGBA",(W,W),(0,0,0,0))
    x0,y0,x1,y1=200,96,824,928; f=180; r=52; ow=30
    sh=Image.new("RGBA",(W,W),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([s(x0+10),s(y0+22),s(x1+10),s(y1+22)],s(r),fill=(0,0,0,70))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(14))))
    def pagepoly(inset,col):
        a,b,c,e=x0+inset,y0+inset,x1-inset,y1-inset; ff=f-inset*0.4; rr=max(r-inset,4)
        m=Image.new("L",(W,W),0); md=ImageDraw.Draw(m)
        md.rounded_rectangle([s(a),s(b),s(c),s(e)],s(rr),fill=255)
        md.polygon([(s(c-ff),s(b)-2),(s(c)+2,s(b)-2),(s(c)+2,s(b+ff))],fill=0)
        im.paste(Image.new("RGBA",(W,W),col),(0,0),m)
    pagepoly(0,INK); pagepoly(ow,CREAM)
    d=ImageDraw.Draw(im)
    d.polygon([(s(x1-f),s(y0)),(s(x1-f),s(y0+f)),(s(x1),s(y0+f))],fill=INK)
    d.polygon([(s(x1-f+ow*0.9),s(y0+ow*2.1)),(s(x1-f+ow*0.9),s(y0+f-ow*0.9)),(s(x1-ow*2.1),s(y0+f-ow*0.9))],fill=FOLD)
    by0=660
    d.rounded_rectangle([s(x0),s(by0),s(x1),s(y1)],s(r),fill=INK)
    d.rectangle([s(x0),s(by0),s(x1),s(by0+r)],fill=INK)
    text(d,512,by0+(y1-by0)/2+4,"PDF",190,hx('FFFFFF'))
    # copper axe head as a bookmark: straight neck, sides flaring in a gentle curve, convex edge
    cx=300; top=40; nw=96; ny=200; by=372; bw=150; n=30
    right=[(cx+nw/2,top),(cx+nw/2,ny)]+[(cx+nw/2+(bw/2-nw/2)*math.sin(t/n*math.pi/2)**1.2, ny+(by-ny)*t/n) for t in range(1,n+1)]
    edge=[(cx+bw/2-bw*i/n, by+16*math.sin(math.pi*i/n)) for i in range(1,n)]
    left=[(2*cx-x,y) for x,y in reversed(right)]
    pts=right+edge+left
    sp=[(s(x),s(y)) for x,y in pts]
    shp=Image.new("RGBA",(W,W),(0,0,0,0)); ImageDraw.Draw(shp).polygon([(x+s(6),y+s(10)) for x,y in sp],fill=(0,0,0,90))
    im.alpha_composite(shp.filter(ImageFilter.GaussianBlur(s(8))))
    d=ImageDraw.Draw(im); d.polygon(sp,fill=COP)
    text(d,512,430,"CH",130,COP)
    return im.resize((1024,1024),Image.LANCZOS)
if __name__=="__main__":
    a=icon(); a.save("v2-1024.png")
    prev=Image.new("RGBA",(760,340),(246,244,240,255))
    prev.alpha_composite(a.resize((300,300),Image.LANCZOS),(20,20))
    for j,sz in enumerate((64,48,32,24,16)):
        sm=a.resize((sz,sz),Image.LANCZOS); prev.alpha_composite(sm,(350+j*80,40+(64-sz)//2))
    strip=Image.new("RGBA",(400,60),(32,32,36,255))
    for j,sz in enumerate((32,24,16)):
        sm=a.resize((sz,sz),Image.LANCZOS); strip.alpha_composite(sm,(20+j*60,(60-sz)//2))
    prev.alpha_composite(strip,(350,160)); prev.save("v2-preview.png")
