#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Terrain (.dsf)...'
Blender: 244
Group: 'Import'
Tooltip: 'Import X-Plane terrain'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "3.09"
__bpydoc__ = """\
This script imports X-Plane DSF terrain into Blender.
"""

#------------------------------------------------------------------------
# X-Plane importer for blender 2.44 or above
#
# Copyright (c) 2006,2007 Jonathan Harris
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
#
# 2006-10-09
#

from Blender import Draw, Window, Image, Lamp, Material, Mesh, Object, Scene, Texture
from Blender.Mathutils import Vector

from math import cos, pi, radians
from os import listdir, walk
from os.path import abspath, basename, dirname, exists, isdir, join, pardir, normpath
from struct import unpack

hscale=1000
vscale=1.0/100
resolution=8*65535
minres=1.0/resolution

libterrain={}


def readDSF(path):
    baddsf=(0, "Invalid DSF file", path)

    h=file(path, 'rb')
    h.seek(0, 2)
    hlen=h.tell()
    h.seek(0, 0)    
    if h.read(8)!='XPLNEDSF' or unpack('<I',h.read(4))!=(1,) or h.read(4)!='DAEH':
        raise IOError, baddsf
    (l,)=unpack('<I', h.read(4))
    headend=h.tell()+l-8
    if h.read(4)!='PORP':
        raise IOError, baddsf
    (l,)=unpack('<I', h.read(4))
    properties=[]
    c=h.read(l-9).split('\0')
    h.read(1)
    overlay=0
    for i in range(0, len(c)-1, 2):
        if c[i]=='sim/overlay': overlay=int(c[i+1])
        elif c[i]=='sim/south': lat=int(c[i+1])
        elif c[i]=='sim/west': lon=int(c[i+1])
        properties.append((c[i],c[i+1]))
    h.seek(headend)
    if overlay:
        # Overlay DSF - bail early
        h.close()
        raise IOError, (0, "This is an overlay DSF", path)

    # Definitions Atom
    if h.read(4)!='NFED':
        raise IOError, baddsf
    (l,)=unpack('<I', h.read(4))
    defnend=h.tell()+l-8
    terrain=objects=polygons=network=[]
    while h.tell()<defnend:
        c=h.read(4)
        (l,)=unpack('<I', h.read(4))
        if l==8:
            pass	# empty
        elif c=='TRET':
            terrain=h.read(l-9).replace('\\','/').replace(':','/').split('\0')
            h.read(1)
        elif c=='TJBO':
            objects=h.read(l-9).replace('\\','/').replace(':','/').split('\0')
            h.read(1)
        elif c=='YLOP':
            polygons=h.read(l-9).replace('\\','/').replace(':','/').split('\0')
            h.read(1)
        elif c=='WTEN':
            networks=h.read(l-9).replace('\\','/').replace(':','/').split('\0')
            h.read(1)
        else:
            h.seek(l-8, 1)

    # Geodata Atom
    if h.read(4)!='DOEG':
        raise IOError, baddsf
    (l,)=unpack('<I', h.read(4))
    geodend=h.tell()+l-8
    pool=[]
    scal=[]
    while h.tell()<geodend:
        c=h.read(4)
        (l,)=unpack('<I', h.read(4))
        if c=='LOOP':
            thispool=[]
            (n,)=unpack('<I', h.read(4))
            (p,)=unpack('<B', h.read(1))
            for i in range(p):
                thisplane=[]
                (e,)=unpack('<B', h.read(1))
                if e==0 or e==1:
                    last=0
                    for j in range(n):
                        (d,)=unpack('<H', h.read(2))
                        if e==1: d=(last+d)&65535
                        thisplane.append(d)
                        last=d
                elif e==2 or e==3:
                    last=0
                    while(len(thisplane))<n:
                        (r,)=unpack('<B', h.read(1))
                        if (r&128):
                            (d,)=unpack('<H', h.read(2))
                            for j in range(r&127):
                                if e==3:
                                    thisplane.append((last+d)&65535)
                                    last=(last+d)&65535
                                else:
                                    thisplane.append(d)
                        else:
                            for j in range(r):
                                (d,)=unpack('<H', h.read(2))
                                if e==3: d=(last+d)&65535
                                thisplane.append(d)
                                last=d
                else:
                    raise IOError, baddsf
                thispool.append(thisplane)  
            pool.append(thispool)
        elif c=='LACS':
            thisscal=[]
            for i in range(0, l-8, 8):
                d=unpack('<2f', h.read(8))
                thisscal.append(d)
            scal.append(thisscal)
        else:
            h.seek(l-8, 1)
    
    # Rescale pool and transform to one list per entry
    if len(scal)!=len(pool): raise(IOError)
    newpool=[]
    for i in range(len(pool)):
        curpool=pool[i]
        n=len(curpool[0])
        newpool=[[] for j in range(n)]
        for plane in range(len(curpool)):
            (scale,offset)=scal[i][plane]
            scale=scale/65535
            for j in range(n):
                newpool[j].append(curpool[plane][j]*scale+offset)
        pool[i]=newpool

    # Commands Atom
    if h.read(4)!='SDMC':
        raise IOError, baddsf
    (l,)=unpack('<I', h.read(4))
    cmdsend=h.tell()+l-8
    curpool=0
    idx=0
    near=0
    far=-1
    flags=0	# 0=physical, 1=overlay
    f=[[[],[]] for i in range(len(terrain))]
    v=[[[],[]] for i in range(len(terrain))]
    t=[[[],[]] for i in range(len(terrain))]
    pscale=99.0/(hlen-geodend)
    progress=0
    while h.tell()<cmdsend:
        now=int((h.tell()-geodend)*pscale)
        if progress!=now:
            progress=now
            Window.DrawProgressBar(progress/100.0, "Importing %2d%%"%progress)
            
        (c,)=unpack('<B', h.read(1))
        if c==1:	# Coordinate Pool Select
            (curpool,)=unpack('<H', h.read(2))
            
        elif c==2:	# Junction Offset Select
            h.read(4)	# not implemented
            
        elif c==3:	# Set Definition
            (idx,)=unpack('<B', h.read(1))
            
        elif c==4:	# Set Definition
            (idx,)=unpack('<H', h.read(2))
            
        elif c==5:	# Set Definition
            (idx,)=unpack('<I', h.read(4))
            
        elif c==6:	# Set Road Subtype
            h.read(1)	# not implemented
            
        elif c==7:	# Object
            h.read(2)	# not implemented
                
        elif c==8:	# Object Range
            h.read(4)	# not implemented
                    
        elif c==9:	# Network Chain
            (l,)=unpack('<B', h.read(1))
            h.read(l*2)	# not implemented
            
        elif c==10:	# Network Chain Range
            h.read(4)	# not implemented
            
        elif c==11:	# Network Chain
            (l,)=unpack('<B', h.read(1))
            h.read(l*4)	# not implemented
            
        elif c==12:	# Polygon
            (param,l)=unpack('<HB', h.read(3))
            h.read(l*2)	# not implemented
            
        elif c==13:	# Polygon Range (DSF2Text uses this one)
            (param,first,last)=unpack('<HHH', h.read(6))	# not implemented
            
        elif c==14:	# Nested Polygon
            (param,n)=unpack('<HB', h.read(3))
            for i in range(n):
                (l,)=unpack('<B', h.read(1))
                h.read(l*2)	# not implemented
                
        elif c==15:	# Nested Polygon Range (DSF2Text uses this one too)
            (param,n)=unpack('<HB', h.read(3))
            h.read((n+1)*2)	# not implemented
            
        elif c==16:	# Terrain Patch
            pass
        
        elif c==17:	# Terrain Patch w/ flags
            (flags,)=unpack('<B', h.read(1))
            flags-=1
            
        elif c==18:	# Terrain Patch w/ flags & LOD
            (flags,near,far)=unpack('<Bff', h.read(9))
            flags-=1

        elif c==23:	# Patch Triangle
            (l,)=unpack('<B', h.read(1))
            n=len(v[idx][flags])
            for i in range(n,n+l,3):
                f[idx][flags].append([i+2,i+1,i])
            for i in range(l):
                (d,)=unpack('<H', h.read(2))
                p=pool[curpool][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])
                    
            
        elif c==24:	# Patch Triangle - cross-pool
            (l,)=unpack('<B', h.read(1))
            n=len(v[idx][flags])
            for i in range(n,n+l,3):
                f[idx][flags].append([i+2,i+1,i])
            for i in range(l):
                (c,d)=unpack('<HH', h.read(4))
                p=pool[c][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])

        elif c==25:	# Patch Triangle Range
            (first,last)=unpack('<HH', h.read(4))
            n=len(v[idx][flags])
            for i in range(n,n+last-first,3):
                f[idx][flags].append([i+2,i+1,i])
            for d in range(first,last):
                p=pool[curpool][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])
            
        #elif c==26:	# Patch Triangle Strip (not used by DSF2Text)
        #elif c==27:
        #elif c==28:
        
        elif c==29:	# Patch Triangle Fan
            (l,)=unpack('<B', h.read(1))
            n=len(v[idx][flags])
            for i in range(1,l-1):
                f[idx][flags].append([n+i+1,n+i,n])
            for i in range(l):
                (d,)=unpack('<H', h.read(2))
                p=pool[curpool][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])
            
        elif c==30:	# Patch Triangle Fan - cross-pool
            (l,)=unpack('<B', h.read(1))
            n=len(v[idx][flags])
            for i in range(1,l-1):
                f[idx][flags].append([n+i+1,n+i,n])
            for i in range(l):
                (c,d)=unpack('<HH', h.read(4))
                p=pool[c][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])

        elif c==31:	# Patch Triangle Fan Range
            (first,last)=unpack('<HH', h.read(4))
            n=len(v[idx][flags])
            for i in range(1,last-first-1):
                f[idx][flags].append([n+i+1,n+i,n])
            for d in range(first, last):
                p=pool[curpool][d]
                v[idx][flags].append([(p[0]-lon)*hscale,
                                      (p[1]-lat)*hscale, p[2]*vscale])
                if len(p)>=7:
                    t[idx][flags].append([p[5],p[6]])

        elif c==32:	# Comment
            (l,)=unpack('<B', h.read(1))
            h.read(l)
            
        elif c==33:	# Comment
            (l,)=unpack('<H', h.read(2))
            h.read(l)
            
        elif c==34:	# Comment
            (l,)=unpack('<I', h.read(4))
            h.read(l)
            
        else:
            raise IOError, (c, "Unrecognised command (%d)" % c, c)

    h.close()

    Window.DrawProgressBar(0.99, "Realising")

    scene=Scene.GetCurrent()
    scene.layers=[1,2]

    for flags in [0]:# was [1,0]:	# overlay first so overlays
        for idx in range(len(terrain)):
            if not f[idx][flags]: continue
            if idx:
                name=basename(terrain[idx])[:-4]
                if flags: name=name+'.2'
                if terrain[idx] in libterrain:
                    (texture, angle, xscale, zscale)=readTER(libterrain[terrain[idx]])
                elif exists(join(dirname(path), pardir, pardir, terrain[idx])):
                    (texture, angle, xscale, zscale)=readTER(abspath(join(dirname(path), pardir, pardir, terrain[idx])))
                else:
                    raise IOError(0, 'Terrain %s not found' % terrain[idx], terrain[idx])
                try:
                    mat=Material.Get(name)
                except:
                    mat=Material.New(name)
                    mat.rgbCol=[1.0, 1.0, 1.0]
                    mat.spec=0
                    try:
                        img=Image.Get(basename(texture))
                    except:
                        img=Image.Load(texture)
                    tex=Texture.New(name)
                    tex.setType('Image')
                    tex.image=img
                    mat.setTexture(0, tex)
                    if flags:
                        mat.zOffset=1
                        mat.mode |= Material.Modes.ZTRANSP
                    mtex=mat.getTextures()[0]
                    mtex.size=(xscale*250, zscale*250, 0)
                    mtex.zproj=Texture.Proj.NONE
                    if t[idx][flags]:
                        mtex.texco=Texture.TexCo.UV
                    else:
                        mtex.texco=Texture.TexCo.GLOB
            else:
                name=terrain[idx]
                mat=Material.New(terrain[idx])
                mat.rgbCol=[0.1, 0.1, 0.2]
                mat.spec=0
            
            mesh=Mesh.New(name)
            mesh.mode &= ~(Mesh.Modes.TWOSIDED|Mesh.Modes.AUTOSMOOTH)
            mesh.mode |= Mesh.Modes.NOVNORMALSFLIP
            mesh.materials += [mat]
            mesh.verts.extend(v[idx][flags])
            mesh.faces.extend(f[idx][flags])
            if t[idx][flags]:
                faceno=0
                for face in mesh.faces:
                    face.uv=[Vector(t[idx][flags][i][0], t[idx][flags][i][1]) for i in f[idx][flags][faceno]]
                    face.image=img
                    faceno+=1
            mesh.update()

            ob = Object.New("Mesh", name)
            ob.link(mesh)
            scene.objects.link(ob)
            ob.Layer=flags+1
            ob.addProperty('terrain', terrain[idx])

            mesh.sel=True
            mesh.remDoubles(0.001)	# must be after linked to object
            mesh.sel=False

        if 0:	# Unreliable
            for face in mesh.faces:
                for v in face.verts:
                    if v.co[2]!=0.0:
                        break
                else:
                    face.mat=1	# water
                    
    lamp=Lamp.New("Lamp", "Sun")
    ob = Object.New("Lamp", "Sun")
    ob.link(lamp)
    scene.objects.link(ob)
    lamp.type=1
    ob.Layer=3
    ob.setLocation(500, 500, 1000)


#------------------------------------------------------------------------
def readTER(path):
    texture=None
    angle=0
    xscale=zscale=0
    h=file(path, 'rU')
    if not (h.readline().strip() in ['I','A'] and
            h.readline().strip()=='800' and
            h.readline().strip()=='TERRAIN'):
        raise IOError, (0, "%s is not a valid terrain file" % path, path)
    for line in h:
        line=line.strip()
        c=line.split()
        if not c: continue
        if c[0] in ['BASE_TEX', 'BASE_TEX_NOWRAP']:
            texture=line[len(c[0]):].strip().replace(':','/').replace('\\','/')
            texture=abspath(join(dirname(path), texture))
        elif c[0]=='PROJECTED':
            xscale=1/float(c[1])
            zscale=1/float(c[2])
        elif c[0]=='PROJECT_ANGLE':
            if float(c[1])==0 and float(c[2])==1 and float(c[3])==0:
                # no idea what rotation about other axes means
                angle=int(float(c[4]))
    h.close()
    return (texture, angle, xscale, zscale)


#------------------------------------------------------------------------
def readLIBs(libpath, libterrain):
    for d in listdir(libpath):
        if not isdir(join(libpath,d)): continue
        for filename in listdir(join(libpath,d)):
            if filename.lower()!='library.txt': continue
            path=join(libpath,d)
            h=open(join(path,filename), 'rU')
            if not h.readline().strip()[0] in ['I','A']:
                raise IOError
            if not h.readline().split()[0]=='800':
                raise IOError
            if not h.readline().split()[0]=='LIBRARY':
                raise IOError
            for line in h:
                c=line.split()
                if not c: continue
                if c[0] in ['EXPORT', 'EXPORT_RATIO', 'EXPORT_EXTEND']:
                    if c[0]=='EXPORT_RATIO': c.pop(1)
                if len(c)<3 or c[1][-4:].lower() not in ['.ter','net']: continue
                c.pop(0)
                name=c[0].replace(':','/').replace('\\','/')
                if not name in libterrain:
                    #if len(basename(name))>25: print basename(name)[:-4], len(basename(name)[:-4])
                    c.pop(0)
                    obj=normpath(join(path, ' '.join(c).replace(':','/').replace('\\','/')))
                    libterrain[name]=obj
            h.close()
            break

        
#------------------------------------------------------------------------
def file_callback (filename):
    print "Starting DSF import from " + filename
    Window.WaitCursor(1)

    if 1:#XXXtry:
        xppath=normpath(join(dirname(filename),pardir,pardir,pardir,pardir))
        dirs=[i.lower() for i in listdir(xppath)]
        if 'default scenery' in dirs and 'custom scenery' not in dirs:
            xppath=normpath(join(xppath,pardir))

        # Process libraries
        Window.DrawProgressBar(0, "Scanning libraries")
        for d in listdir(xppath):
            if d.lower()=='custom scenery':
                readLIBs(join(xppath,d), libterrain)
                break
        for d in listdir(xppath):
            if d.lower()=='resources':
                for d2 in listdir(join(xppath,d)):
                    if d2.lower()=='default scenery':
                        readLIBs(join(xppath,d,d2), libterrain)
                        break
                break
        
        Window.DrawProgressBar(0, "Importing")
        readDSF(filename)
    elif 0:#except IOError, e:
        Window.WaitCursor(0)
        Window.DrawProgressBar(1, "ERROR")
        print("ERROR:\t%s.\n" % e.strerror)
        Draw.PupMenu("ERROR: %s" % e.strerror)
        return
    elif 0:#except:
        Window.WaitCursor(0)
        Window.DrawProgressBar(1, "ERROR")
        print("ERROR:\tCan't read DSF.\n")
        Draw.PupMenu("ERROR: Can't read DSF")
        return
    else:
        Window.WaitCursor(0)
    Window.DrawProgressBar(1, "Finished")
    Window.RedrawAll()
    print "Finished\n"


#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

Window.FileSelector(file_callback,"Import DSF")
