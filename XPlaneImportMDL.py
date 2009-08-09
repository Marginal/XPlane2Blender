#!BPY
""" Registration info for Blender menus:
Name: 'FS9/FSX Model (.mdl)...'
Blender: 245
Group: 'Import'
Tooltip: 'Import a FS9 or FSX aircraft or scenery model (.mdl)'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "0.30"
__bpydoc__ = """\
This script imports Microsoft Flight Simulator 9 and X models into Blender
for editing and export as an X-Plane object.
"""

#------------------------------------------------------------------------
# MDL importer for blender 2.45 or above
#
# Copyright (c) 2008, 2009 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-Noncommercial-Share Alike 3.0:
#
#   You are free:
#    * to Share - to copy, distribute and transmit the work
#    * to Remix - to adapt the work
#
#   Under the following conditions:
#    * Attribution. You must attribute the work in the manner specified
#      by the author or licensor (but not in any way that suggests that
#      they endorse you or your use of the work).
#    * Noncommercial. You may not use this work for commercial purposes.
#    * Share Alike. If you alter, transform, or build upon this work,
#      you may distribute the resulting work only under the same or
#      similar license to this one.
#
#   For any reuse or distribution, you must make clear to others the
#   license terms of this work.
#
# This is a human-readable summary of the Legal Code (the full license):
#   http://creativecommons.org/licenses/by-nc-sa/3.0/
#

from Blender import Image, Material, Mesh, Object, Scene, Texture, Draw, Window
from Blender.Mathutils import Matrix, Euler, Vector, RotationMatrix, TranslationMatrix

from os import listdir
from os.path import basename, dirname, join, normpath, pardir, splitext
from struct import unpack

debug=False

# Number of decimal places
VROUND=6

# flags
ISSPECULAR=	0x00000001
DIFFUSE=	0x00000002
BUMP=		0x00000004
SPECULAR=	0x00000008
DETAIL=		0x00000010
ENVMAP=		0x00000020
GLOBALENVMAP=	0x00000040
EMISSIVE=	0x00000080
FRESNELREFL=	0x00000100
FRESNELDIFF=	0x00000200
FRESNELSPEC=	0x00000400
PRECIPOFFSET=	0x00000800
PRECIPITATION=	0x00001000
ENVINVDIFALPHA=	0x00002000
ENVSPECALPHA=	0x00004000
VERTICALNORM=	0x00008000
ZWRITEALPHA=	0x00010000
NOZWRITE=	0x00020000
BLOOMBYCOPY=	0x00040000
BLOOMBYALPHA=	0x00080000
VOLUMESHADOW=	0x00100000
NOSHADOW=	0x00200000
ZTESTALPHA=	0x00400000
FINALALPHABLEND=0x01000000
SKINNEDMESH=	0x04000000
ALLOWBLOOM=	0x08000000
EMISSIIVEBLOOM=	0x10000000
DIFDIFALPHA=	0x20000000
DIFISPECALPHA=	0x40000000
PRELITVERTICES=	0x80000000

# flags2
BLENDCONSTANT=	0x0001
TEXTUREWRAP=	0x0002
TEXTURECLAMP=	0x0004
DOUBLESIDED=	0x0008	# XXX do me
EMADDNOUSR=	0x0010
EMMUL=		0x0040
EMMULUSR=	0x0080
EMADD=		0x0100
EMADDUSR=	0x0200

# blend
BLEND_ZERO=1
BLEND_ONE=2
BLEND_SRCCLR=3
BLEND_INVSRCCLR=4
BLEND_SRCALPHA=5
BLEND_INVSRCALPHA=6
BLEND_DSTALPHA=7
BLEND_INVDSTALPHA=8
BLEND_DSTCLR=9
BLEND_INVFSTCLR=10

# Platform surfaces in MDL type order
SURFACES=['CONCRETE', 'GRASS', 'WATER', 'GRASS_BUMPY', 'ASPHALT', 'SHORT_GRASS', 'LONG_GRASS', 'HARD_TURF', 'SNOW', 'ICE', 'URBAN', 'FOREST', 'DIRT', 'CORAL', 'GRAVEL', 'OIL_TREATED', 'STEEL_MATS', 'BITUMINUS', 'BRICK', 'MACADAM', 'PLANKS', 'SAND', 'SHALE', 'TARMAC', 'WRIGHT_FLYER_TRACK']


# Create FSX LOD properties
def addprops(scene, lods):
    try:
        propobj=Object.Get('FSXProperties')
        propobj.removeAllProperties()
    except:
        propobj=Object.New('Empty', 'FSXProperties')
        scene.objects.link(propobj)
        propobj.layers=[]	# invisible
    for layer in range(min(10,len(lods))):
        propobj.addProperty('LOD_%02d' % (layer+1), lods[layer])


# Create attach point
def addattach(scene, name, matrix):
    if name.startswith('attachpt_'): name=name[9:]
    if not name: name='AttachPoint'
    obj=Object.New('Empty', name)
    scene.objects.link(obj)
    obj.layers=[1]
    obj.addProperty('name', obj.name)

    # Need to convert between right and left handed coordinate systems.
    obj.setMatrix(RotationMatrix(-90,4,'x')*matrix*Matrix([1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]))
    obj.LocY=-obj.LocY


    return obj


# Create Blender object
def adddata(scene, layer, material, vert, inde, matrix, plat=None):
    # Need to convert between right and left handed coordinate systems.
    matrix=matrix*Matrix([1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1])

    # This results in a negatively scaled matrix, which causes  problems
    # for face normals. So separate out and apply scale&rotation parts.
    tran=TranslationMatrix(matrix.translationPart())
    matrix[3]=[0,0,0,1]

    # detect back-to-back duplicate faces
    facelookup={}
    newvert=[[]]
    for i in range(0, len(inde), 3):
        face=[(vert[inde[j]][0], vert[inde[j]][1], vert[inde[j]][2]) for j in range(i+2,i-1,-1)]
        # duplicate faces may be rotated - eg Oil_Rig_Sample
        if tuple(face) in facelookup or (face[1],face[2],face[0]) in facelookup or (face[2],face[0],face[1]) in facelookup:
            # back-to-back duplicate - start new mesh
            newvert.append([])
            facelookup={}
        face.reverse()
        facelookup[tuple(face)]=True
        newvert[-1].extend([vert[inde[j]] for j in range(i,i+3)])

    for vert in newvert:
        mesh=Mesh.New('Mesh')
        mesh.mode &= ~(Mesh.Modes.TWOSIDED|Mesh.Modes.AUTOSMOOTH)
        mesh.mode |= Mesh.Modes.NOVNORMALSFLIP
        mesh.materials+=[material]
        mesh.verts.extend([v[0:3] for v in vert])
        mesh.faces.extend([[i,i+1,i+2] for i in range(0, len(vert), 3)], ignoreDups=True)
        mesh.faceUV=True

        mtex=material.getTextures()[0]
        if mtex:
            image=mtex.tex.image
        else:
            image=None

        surface=None

        i=0
        for face in mesh.faces:
            face.mode &= ~(Mesh.FaceModes.TWOSIDE|Mesh.FaceModes.TILES)
            if image:
                face.mode|=Mesh.FaceModes.TEX
                face.image=image
            face.uv=[Vector(v[6],1-v[7]) for v in [vert[j] for j in range(i,i+3)]]
            # smooth if vertex normals are different
            face.smooth=not (vert[i][3:6]==vert[i+1][3:6]==vert[i+2][3:6])

            # is this a platform?
            if plat:
                v=(vert[i][:3], vert[i+1][:3], vert[i+2][:3])
                #for vt in v: print "%.4f %.4f %.4f" % vt
                #print
                if v in plat:
                    face.mode&=~Mesh.FaceModes.DYNAMIC
                    surface=plat.pop(v)
                else:
                    face.mode |= Mesh.FaceModes.DYNAMIC
            else:
                face.mode |= Mesh.FaceModes.DYNAMIC
                
            i+=3

        ob = Object.New('Mesh')
        ob.link(mesh)
        scene.objects.link(ob)
        ob.layers=[layer]
        ob.setMatrix(tran)
        if surface!=None: ob.addProperty('surfaceType', SURFACES[surface])

        # following must be after object linked to scene
        mesh.transform(matrix)
        mesh.sel=True
        mesh.remDoubles(0.001)	# 1/10mm
        mesh.sel=True
        mesh.calcNormals()	# calculate vertex normals
        mesh.sel=False

         
#------------------------------------------------------------------------
def gettexture(name, dirname, filename):
    (filename,ext)=splitext(basename(filename).lower())
    img=None
    for d in [dirname, normpath(join(dirname, pardir, 'texture'))]:
        for e in ['.png', '.psd', '.jpg', '.jpeg', '.tga', '.bmp', '.dds',ext]:
            try:
                img=Image.Load(join(d,filename+e))
                img.getSize()	# force attempt to load image
                break
            except:
                pass
        else:
            continue

    # Re-use existing
    for tex in Texture.Get():
        if tex.name.startswith(name) and tex.type==Texture.Types.IMAGE and tex.image==img:
            return tex

    tex=Texture.New(name)
    tex.type=Texture.Types.IMAGE
    if img: tex.image=img

    return tex
    

#------------------------------------------------------------------------
def getmaterial9(bgldir, m, matlist, t, texnames):
    (dr,dg,db,da,ar,ag,ab,aa,sr,sg,sb,sa,er,eg,eb,ea,sp)=matlist[m]
    texcount=0
    mat=Material.New()
    mat.rgbCol=[dr,dg,db]
    mat.alpha=da
    mat.specCol=[sr,sg,sb]
    mat.hard=int(sp+0.5)

    diffuse=night=reflect=light=None
    i=t
    for i in range(t,len(texnames)):
        if i==-1: break
        (cls, rgba, reserved, size, name)=texnames[i]
        if i>t and not cls&0xff00: break	# TEXTURE2_MASK
        if cls==1 or cls==6:		# TEXTURE_AIRCRAFT, TEXTURE_BUILDING
            diffuse=name
        elif cls==0x100:		# TEXTURE2_NIGHT
            night=name
        elif cls==0x200:		# TEXTURE2_REFLECT
            reflect=name
        elif cls==0x300 or cls==0x400:	# TEXTURE2_LIGHTMAP, TEXTURE2_LIGHTMAP_A
            light=name

    if diffuse:
        tex=gettexture('Diffuse', bgldir, diffuse)
        mat.setTexture(texcount, tex)
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.COL
        if diffuse==reflect:
            mtex.mapto|=Texture.MapTo.REF
            mtex.mtRef=-1
        texcount+=1

    if night or light:
        if light:
            mat.setTexture(texcount, gettexture('Emissive', bgldir, light))
        else:
            mat.setTexture(texcount, gettexture('Emissive', bgldir, night))
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.EMIT
        if light:
            mtex.blendmode=Texture.BlendModes.ADD
        else:	# default / FS2004 syle - night
            mtex.blendmode=Texture.BlendModes.MIX
        texcount+=1

    return mat


#------------------------------------------------------------------------
def getmaterialx(data, bgldir, texnames):

    (flags,flags2,diffuse,detail,bumpmap,specular,emissive,reflection,fresnel,dr,dg,db,da,sr,sg,sb,sa,sp,detailtile,bumptile,reflectionscale,precipoffset,bloomfloor,amb,unk,srcblend,dstblend,alphafunc,alphathreshold,alphamultiply)=unpack('<9I4f4ff4f2ffIIIff', data)
    if debug: print "%x %x %s" % (flags,flags2,(diffuse,detail,bumpmap,specular,emissive,reflection,fresnel,dr,dg,db,da,sr,sg,sb,sa,sp,detailtile,bumptile,reflectionscale,precipoffset,bloomfloor,amb,unk,srcblend,dstblend,alphafunc,alphathreshold,alphamultiply))

    texcount=0
    mat=Material.New()
    mat.rgbCol=[dr,dg,db]
    mat.alpha=da
    mat.specCol=[sr,sg,sb]
    mat.hard=int(sp+0.5)
    mat.amb=amb

    if flags&VERTICALNORM:
        mat.mode&=~Material.Modes.SHADELESS
    else:
        mat.mode|= Material.Modes.SHADELESS

    if flags&ZWRITEALPHA:
        mat.mode|= Material.Modes.ZTRANSP
    else:
        mat.mode&=~Material.Modes.ZTRANSP

    if flags&VOLUMESHADOW or not flags&NOSHADOW:
        mat.mode|= Material.Modes.SHADOWBUF
    else:
        mat.mode&=~Material.Modes.SHADOWBUF

    if flags&DIFFUSE:
        tex=gettexture('Diffuse', bgldir, texnames[diffuse])
        if srcblend==BLEND_SRCALPHA or flags&ENVINVDIFALPHA:
            tex.imageFlags|=Texture.ImageFlags.USEALPHA
        elif srcblend==BLEND_INVSRCALPHA:
            tex.imageFlags|=Texture.ImageFlags.USEALPHA
            tex.flags|=Texture.Flags.NEGALPHA
        mat.setTexture(texcount, tex)
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.COL
        if dstblend==BLEND_SRCALPHA:
            mtex.mapto|=Texture.MapTo.ALPHA
            mtex.dvar=0.0
            mat.mode|= Material.Modes.ZTRANSP
        elif dstblend==BLEND_INVSRCALPHA:
            mtex.mapto|=Texture.MapTo.ALPHA
            mtex.mtAlpha=-1
            mtex.dvar=0.0
            mat.mode|= Material.Modes.ZTRANSP
        if flags&ENVINVDIFALPHA:
            mtex.mapto|=Texture.MapTo.REF
            mtex.mtRef=-1
        texcount+=1

    if flags&DETAIL:
        mat.setTexture(texcount, gettexture('Detail', bgldir, texnames[detail]))
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.COL
        mtex.colfac=0.5
        mtex.size=(detailtile,detailtile,detailtile)
        texcount+=1

    if flags&BUMP:
        mat.setTexture(texcount, gettexture('BumpMap', bgldir, texnames[bumpmap]))
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.NOR
        mtex.size=(bumptile,bumptile,bumptile)
        texcount+=1

    if flags&SPECULAR:
        tex=gettexture('Specular', bgldir, texnames[specular])
        tex.imageFlags|=Texture.ImageFlags.USEALPHA
        mat.setTexture(texcount, tex)
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.CSP
        if flags&ENVSPECALPHA:
            mtex.mapto|=Texture.MapTo.REF
        texcount+=1
    if flags&ISSPECULAR:
        mat.spec=0.5
    else:
        mat.spec=0

    if flags&ENVMAP or flags&GLOBALENVMAP:
        if flags&ENVMAP:
            tex=gettexture('EnvMap', bgldir, texnames[reflection])
        else:
            try:
                tex=Texture.Get('DefaultEnvMap')
            except:
                tex=Texture.New('DefaultEnvMap')                
        tex.type=Texture.Types.ENVMAP
        tex.stype=Texture.STypes.ENV_LOAD
        mat.setTexture(texcount, tex)
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.REFL
        mtex.mapto=Texture.MapTo.CMIR
        mtex.colfac=reflectionscale
        texcount+=1

    if flags&EMISSIVE:
        mat.setTexture(texcount, gettexture('Emissive', bgldir, texnames[emissive]))
        mtex=mat.getTextures()[texcount]
        mtex.texco=Texture.TexCo.UV
        mtex.mapto=Texture.MapTo.EMIT
        if flags2&EMADD or flags2&EMADDUSR or flags2&EMADDNOUSR:
            mtex.blendmode=Texture.BlendModes.ADD
        elif flags2&EMMUL or flags2&EMMULUSR:
            mtex.blendmode=Texture.BlendModes.MULTIPLY
        else:	# default / FS2004 syle
            mtex.blendmode=Texture.BlendModes.MIX
        texcount+=1

    return mat


#------------------------------------------------------------------------
def container(bgl, indent):
    (c,size)=unpack('<4sI', bgl.read(8))
    if debug: print '%s%s %x' % ('  ' * indent, c, size)
    return (c, size, bgl.tell()+size)


#------------------------------------------------------------------------
def file_callback (filename):
    try:
        bgl=file(filename,'rb')
    except:
        Draw.PupMenu("ERROR%%t|Can't open %s" % filename)
        return

    bgldir=dirname(filename)

    guid=None
    friendly=None
    texnames=[]	# list of texture file names
    matlist=[]	# fs9 materials
    mats=[]	# list of Blender Materials
    inde=[]
    vert=[]
    tran=[]
    amap=[]	# fsx map
    scen=[]	# (child, peer, matrix, parent)
    
    data={}	# (material, vert, inde, scene) by LOD
    plat={}	# (surface, vertices) by scene
    atta=[]	# (name, scene)
    attobjs=[]
    atteffects=[]
    partcount=0

    Window.WaitCursor(1)
    Window.DrawProgressBar(0, "Opening ...")
    try:
        (c,size,endmdl)=container(bgl,0)
        assert (c=='RIFF')
        assert (bgl.read(4) in ['MDL9','MDLX'])
        while bgl.tell()<endmdl:
            (c,size,end1)=container(bgl,1)
            if c=='MDLG':	# FSX guid
                guid='{%x-%x-%x-%x%x-%x%x%x%x%x%x}' % unpack('<IHH8B',bgl.read(size))
                if debug: print guid
            elif c=='MDLH':
                if size==36:	# FS9 header
                    (size,reserved,reserved,radius,reserved,reserved,reserved,reserved,reserved)=unpack('<9I', bgl.read(size))
                    if debug: print radius
                else:
                    bgl.seek(size,1)
            elif c=='MDLN':	# FSX friendly name
                friendly=bgl.read(size).strip('\0').strip()
                if debug: print friendly
            elif c=='MDLD':	# FSX data
                while bgl.tell()<end1:
                    Window.DrawProgressBar(float(bgl.tell())/(endmdl+endmdl), "Reading ...")
                    (c,size,end2)=container(bgl,2)
                    if c=='TEXT':
                        texnames=[bgl.read(64).strip('\0').strip() for i in range(0,size,64)]
                    elif c=='MATE':
                        mats.extend([getmaterialx(bgl.read(120), bgldir, texnames) for i in range(0,size,120)])
                    elif c=='INDE':
                        # reverse order of vertices in each triangle
                        for i in range(size/6):
                            t=list(unpack('<3H', bgl.read(6)))
                            t.reverse()
                            inde.extend(t)
                    elif c=='VERB':
                        while bgl.tell()<end2:
                            (c,size,end3)=container(bgl,3)
                            if c=='VERT':
                                vert.append([tuple([round(i,VROUND) for i in unpack('<8f',bgl.read(32))]) for j in range(0,size,32)])
                            else:
                                bgl.seek(size,1)
                    elif c=='TRAN':
                        for i in range(0,size,64):
                            tran.append(Matrix(*[unpack('<4f',bgl.read(16)) for j in range(4)]))
                    elif c=='AMAP':
                        for i in range(0,size,8):
                            (a,b)=unpack('<2I',bgl.read(8))
                            amap.append(b)
                    elif c=='SCEN':
                        # Assumed to be after TRAN and AMAP sections
                        count=size/8
                        for i in range(count):
                            (child,peer,offset,unk)=unpack('<4h',bgl.read(8))
                            thismatrix=tran[amap[offset/8]]
                            scen.append((child,peer,thismatrix,-1))
                    elif c=='LODT':
                        while bgl.tell()<end2:
                            (c,size,end3)=container(bgl,3)
                            if c=='LODE':
                                (lod,)=unpack('<I', bgl.read(4))
                                while bgl.tell()<end3:
                                    (c,size,end4)=container(bgl,4)
                                    if c=='PART':
                                        (typ,sceneg,material,verb,voff,vcount,ioff,icount,mouserect)=unpack('<9I', bgl.read(36))
                                        if debug: print lod, typ,sceneg,material,verb,voff,vcount,ioff,icount,mouserect
                                        assert (typ==1)	# TRIANGLE_LIST
                                        if not lod in data: data[lod]=[]
                                        data[lod].append((mats[material], vert[verb][voff:voff+vcount], inde[ioff:ioff+icount], sceneg))
                                        partcount+=1
                                    else:
                                        bgl.seek(size,1)
                            else:
                                bgl.seek(size,1)
                    elif c=='PLAL':
                        while bgl.tell()<end2:
                            (c,size,end3)=container(bgl,3)
                            if c=='PLAT':
                                (surface,sceneg,numvert,v0x,v0y,v0z,v1x,v1y,v1z,v2x,v2y,v2z)=unpack('<3I9f', bgl.read(48))
                                assert (numvert==3)
                                #print (surface,scene,numvert,v0x,v0y,v0z,v1x,v1y,v1z,v2x,v2y,v2z)
                                if not sceneg in plat: plat[sceneg]={}
                                plat[sceneg][((round(v2x,VROUND),round(v2y,VROUND),round(v2z,VROUND)),(round(v1x,VROUND),round(v1y,VROUND),round(v1z,VROUND)),(round(v0x,VROUND),round(v0y,VROUND),round(v0z,VROUND)))]=surface
                            else:
                                bgl.seek(size,1)
                    elif c=='REFL':
                        while bgl.tell()<end2:
                            (c,size,end3)=container(bgl,3)
                            if c=='REFP':
                                (sceneg,size)=unpack('<II', bgl.read(8))
                                
                                atta.append((bgl.read(size).strip('\0').strip(),sceneg))
                            else:
                                bgl.seek(size,1)
                    elif c=='ATTO':
                        while bgl.tell()<end2:
                            (unk,flags,size)=unpack('<IHH', bgl.read(8))
                            d=bgl.read(size)
                            if flags==2:	# Attached object
                                attobjs.append((d[40:-5], '{%x-%x-%x-%x%x-%x%x%x%x%x%x}' % unpack('<IHH8B', d[20:36])))
                            elif flags==4:	# Attached effect
                                p=d[100:-5].split('\0')	# params, attachpt
                                atteffects.append((p[1], d[20:100].strip(' \0'), p[0]))
                            elif debug:
                                print "Unknown attach %d:\n%s" % (flags, d)
                    else:
                        bgl.seek(size,1)
            elif c=='EXTE':	# FS9 data
                while bgl.tell()<end1:
                    Window.DrawProgressBar(float(bgl.tell())/(endmdl+endmdl), "Reading ...")
                    (c,size,end2)=container(bgl,2)
                    if c=='TEXT':
                        (bglop,count,reserved)=unpack('<HHI', bgl.read(8))
                        assert(bglop==0xb7)
                        texnames=[unpack('<4I', bgl.read(16)) + (bgl.read(64).strip('\0').strip(),) for i in range(count)]
                        assert (bgl.read(2)=='\x22\0')	# return
                    elif c=='MATE':
                        (bglop,count,reserved)=unpack('<HHI', bgl.read(8))
                        assert(bglop==0xb6)
                        matlist.extend([unpack('<17f', bgl.read(17*4)) for i in range(count)])
                        assert (bgl.read(2)=='\x22\0')	# return
                    elif c=='VERT':
                        (bglop,count,reserved)=unpack('<HHI', bgl.read(8))
                        assert(bglop==0xb5)
                        vert.extend([tuple([round(i,VROUND) for i in unpack('<8f',bgl.read(32))]) for j in range(count)])
                        assert (bgl.read(2)=='\x22\0')	# return
                    elif c=='BGL ':
                        code=bgl.read(size)
                        lods=[0]
                        lodno=0
                        while lodno<len(lods):
                            ip=0
                            lod=lods[lodno]
                            sceneg=0
                            curmat=None
                            stack=[]
                            if debug: print "LOD >", lod
                            while True:
                                (bglop,)=unpack('<H', code[ip:ip+2])
                                if debug: print "%s%04x: %02x" % ('  '*len(stack), ip, bglop)
                                ip+=2
                                # mostly just opcodes from BGLFP.doc
                                if bglop==0x0d:		# BGL_JUMP
                                    (offset,)=unpack('<h', code[ip:ip+2])
                                    ip=ip-2+offset
                                elif bglop==0x22:	# BGLOP_RETURN
                                    ip=stack.pop()
                                elif bglop==0x23:	# BGLOP_CALL
                                    (offset,)=unpack('<h', code[ip:ip+2])
                                    stack.append(ip+2)
                                    ip=ip-2+offset
                                elif bglop==0x24:	# BGLOP_IFIN1
                                    ip+=8	# assume true
                                elif bglop==0x39:	# BGLOP_IFMASK
                                    ip+=6	# assume true
                                elif bglop==0x5f:	# BGLOP_IFSIZEV
                                    (offset,r,pixels)=unpack('<hHH', code[ip:ip+6])
                                    newlod=int(0.5+radius*2475.0/r)
                                    if newlod not in lods:
                                        lods.append(newlod)
                                    if lod<newlod:
                                        ip=ip-2+offset
                                    else:
                                        ip+=6
                                elif bglop==0x88:	# BGLOP_JUMP_32
                                    (offset,)=unpack('<i', code[ip:ip+4])
                                    ip=ip-2+offset
                                elif bglop==0x89:	# BGLOP_JUMP_32
                                    (offset,)=unpack('<i', code[ip:ip+4])
                                    assert (offset==-1)
                                    ip=ip+4
                                elif bglop==0x8a:	# BGLOP_CALL_32
                                    (offset,)=unpack('<i', code[ip:ip+4])
                                    stack.append(ip+4)
                                    ip=ip-2+offset
                                elif bglop==0xa7:	# BGLOP_SPRITE_VICALL
                                    ip+=20	# ignore
                                elif bglop==0xb3:	# BGLOP_IFINF1
                                    ip+=14	# assume true
                                elif bglop==0xb8:	# BGLOP_SET_MATERIAL
                                    (m,t)=unpack('<hh', code[ip:ip+4])
                                    ip+=4
                                    curmat=getmaterial9(bgldir, m, matlist, t, texnames)
                                elif bglop==0xb9:	# BGLOP_DRAW_TRILIST
                                    (voff,vcount,icount)=unpack('<3H', code[ip:ip+6])
                                    ip+=6
                                    inde=unpack('<%dH' % icount, code[ip:ip+2*icount])
                                    ip+=2*icount
                                    if debug: print "DATA:", lod, sceneg, voff,vcount,icount
                                    if not lod in data: data[lod]=[]
                                    data[lod].append((curmat, vert[voff:voff+vcount], inde, sceneg))
                                    partcount+=1
                                elif bglop==0xbd:	# BGLOP_END
                                    break
                                elif bglop==0xc4:	# BGLOP_SET_MATRIX_INDIRECT
                                    (sceneg,)=unpack('<H', code[ip:ip+2])
                                    ip+=2
                                else:
                                    assert 0
                            lodno+=1

                        # Shift LODs up
                        lods.sort()
                        lods.append(100)
                        for i in range(len(lods)-1,0,-1):
                            data[lods[i]]=data[lods[i-1]]
                        data[lods[0]].pop()
        
                    elif c=='TRAN':
                        for i in range(0,size,64):
                            tran.append(Matrix(*[unpack('<4f',bgl.read(16)) for j in range(4)]))
                            if debug:
                                print i/64
                                print tran[i/64]
                    elif c=='ANIC':
                        anicbase=bgl.tell()
                        amap=bgl.read(size)
                    elif c=='SCEN':
                        # Assumed to be after TRAN and ANIC sections
                        (count,)=unpack('<H', bgl.read(2))
                        scen=[None for i in range(count)]
                        for i in range(count):
                            (n,child,peer,size,offset)=unpack('<4hi', bgl.read(12))
                            offset=bgl.tell()-12+offset-anicbase
                            if size==6:	# Static
                                (bglop,src,dst)=unpack('<3H', amap[offset:offset+6])
                                assert (bglop==0xc6)
                                thismatrix=tran[src]
                            else:	# Animation
                                (x,y,z,dst)=unpack('<3fh', amap[offset+size-14:offset+size])
                                thismatrix=TranslationMatrix(Vector(x,y,z,0))
                            
                            scen[n]=(child,peer,thismatrix,-1)
                    elif c=='PLAT':
                        (count,)=unpack('<I', bgl.read(4))
                        s=[]
                        for i in range(count):
                            (sceneg,offset,numvert,surface)=unpack('<HhHH', bgl.read(8))
                            assert (numvert==3)	# triangle
                            s.append((sceneg,surface))
                        # Assumes in order so can ignore offset
                        for i in range(count):
                            (sceneg,surface)=s[i]
                            (v0x,v0y,v0z,v1x,v1y,v1z,v2x,v2y,v2z)=unpack('9f', bgl.read(36))
                            if not sceneg in plat: plat[sceneg]={}
                            plat[sceneg][((round(v0x,VROUND),round(v0y,VROUND),round(v0z,VROUND)),(round(v1x,VROUND),round(v1y,VROUND),round(v1z,VROUND)),(round(v2x,VROUND),round(v2y,VROUND),round(v2z,VROUND)))]=surface

                    elif c=='ATTA':
                        (count,)=unpack('<I', bgl.read(4))
                        s=[]
                        for i in range(count):
                            (sceneg,offset)=unpack('<Hh', bgl.read(4))
                            s.append((sceneg))
                        # Assumes in order so can ignore offset
                        for i in range(count):
                            name=''
                            while True:
                                c=bgl.read(1)
                                if c=='\0': break
                                name=name+c
                            atta.append((name.strip(),s[i]))
                    elif c=='ATTO':		# same as FSX
                        while bgl.tell()<end2:
                            (unk,flags,size)=unpack('<IHH', bgl.read(8))
                            d=bgl.read(size)
                            if flags==2:	# Attached object
                                attobjs.append((d[40:-5], '{%x-%x-%x-%x%x-%x%x%x%x%x%x}' % unpack('<IHH8B', d[20:36])))
                            elif flags==4:	# Attached effect
                                p=d[100:-5].split('\0')	# params, attachpt
                                atteffects.append((p[1], d[20:100].strip(' \0'), p[0]))
                            elif debug:
                                print "Unknown attach %d:\n%s" % (flags, d)
                    else:
                        bgl.seek(size,1)
            else:
                bgl.seek(size,1)

        bgl.close()

        # Invert Child/Peer pointers to get parents
        for i in range(len(scen)):
            (child, peer, thismatrix, parent)=scen[i]
            if child!=-1:	# child's parent is me
                (xchild, xpeer, xmatrix, xparent)=scen[child]
                scen[child]=(xchild, xpeer, xmatrix, i)
            if peer!=-1:	# peer's parent is my parent
                assert (peer>i)
                (xchild, xpeer, xmatrix, xparent)=scen[peer]
                scen[peer]=(xchild, xpeer, xmatrix, parent)
        if debug:
            print "TRAN Matrices", len(tran)
            for i in range(len(tran)):
                print i
                print tran[i]
            #print "Animation map", len(amap)
            #for i in range(len(amap)):
            #    print i, '->', amap[i]
            print "Scene Graph", len(scen)
            for i in range(len(scen)):
                (child, peer, thismatrix, parent)=scen[i]
                print i, child, peer, parent
                print thismatrix

        scene=Scene.GetCurrent()
        lods=data.keys()
        lods.sort()
        lods.reverse()
        partno=0.0
        for layer in range(len(lods)):
            for (material, vert, inde, sceneg) in data[lods[layer]]:
                Window.DrawProgressBar(0.5+partno/(partcount+partcount), "Adding ...")
                (child, peer, finalmatrix, parent)=scen[sceneg]
                #print lods[layer]
                #print sceneg, child, peer, parent
                while parent!=-1:
                    (child, peer, thismatrix, parent)=scen[parent]
                    finalmatrix=finalmatrix*thismatrix
                #print finalmatrix
                if not layer and sceneg in plat:
                    adddata(scene, layer+1, material, vert, inde, finalmatrix, plat[sceneg])
                else:
                    adddata(scene, layer+1, material, vert, inde, finalmatrix)
                partno+=1
        if debug:
            for (sceneg,verts) in plat.iteritems():
                if verts:
                    print "Unallocated platforms: sceneg=%d, %d:" % (sceneg, len(verts.keys()))
                    for v in verts.keys():
                        for vt in v: print "%.4f %.4f %.4f" % vt
                        print

        # Attach points
        attachpoints={}
        for (name, sceneg) in atta:
            (child, peer, finalmatrix, parent)=scen[sceneg]
            while parent!=-1:
                (child, peer, thismatrix, parent)=scen[parent]
                finalmatrix=finalmatrix*thismatrix
            attachpoints[name]=addattach(scene, name, finalmatrix)
        for (name, obj) in attobjs:
            attachpoints[name].addProperty('guid', obj)
        for (name, effect, params) in atteffects:
            attachpoints[name].addProperty('effectName', effect)
            if params: attachpoints[name].addProperty('effectParams', params)


        addprops(scene, lods)
        
        Window.DrawProgressBar(1, "Finished")
        Window.WaitCursor(0)

    except:
        bgl.close()
        Window.DrawProgressBar(1, "ERROR")
        Window.WaitCursor(0)
        Draw.PupMenu("ERROR%%t|Can't read %s - is this a FSX MDL format file?" % filename)


#------------------------------------------------------------------------
Window.FileSelector (file_callback,"Import MDL")
