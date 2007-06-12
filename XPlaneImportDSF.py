#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Terrain (.dsf)...'
Blender: 243
Group: 'Import'
Tooltip: 'Import X-Plane terrain'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "2.38"
__bpydoc__ = """\
This script imports X-Plane DSF terrain into Blender.
"""

#------------------------------------------------------------------------
# X-Plane importer for blender 2.42 or above
#
# Copyright (c) 2006,2007 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-ShareAlike 2.5:
#
#   You are free:
#     * to copy, distribute, display, and perform the work
#     * to make derivative works
#     * to make commercial use of the work
#   Under the following conditions:
#     * Attribution: You must give the original author credit.
#     * Share Alike: If you alter, transform, or build upon this work, you
#       may distribute the resulting work only under a license identical to
#       this one.
#   For any reuse or distribution, you must make clear to others the license
#   terms of this work.
#
# This is a human-readable summary of the Legal Code (the full license):
#   http://creativecommons.org/licenses/by-sa/2.5/legalcode
#
#
# 2006-10-09
#

from Blender import Draw, Window, Object, Mesh, Material, Scene
from math import cos, pi
from struct import unpack

onedeg=1852*60		# 1 degree of longitude at equator (60nm)
d2r=pi/180.0


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
        elif c[i]=='sim/south': centrelat=int(c[i+1])+0.5
        elif c[i]=='sim/west': centrelon=int(c[i+1])+0.5
        properties.append((c[i],c[i+1]))
    h.seek(headend)
    if overlay:
        # Overlay DSF - bail early
        h.close()
        return

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
        for plane in range(3):	# Only do lon,lat and height # (len(curpool)):
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
    f=[[],[]]
    v=[[],[]]
    hscale=99.0/(hlen-geodend)
    progress=0
    while h.tell()<cmdsend:
        now=int((h.tell()-geodend)*hscale)
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
            n=len(v[flags])
            for i in range(n,n+l,3):
                if idx:	# not water
                    f[flags].append([i+2,i+1,i])
            for i in range(l):
                (d,)=unpack('<H', h.read(2))
                if idx:	# not water
                    p=pool[curpool][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])
            
        elif c==24:	# Patch Triangle - cross-pool
            (l,)=unpack('<B', h.read(1))
            n=len(v[flags])
            for i in range(n,n+l,3):
                if idx:	# not water
                    f[flags].append([i+2,i+1,i])
            for i in range(l):
                (c,d)=unpack('<HH', h.read(4))
                if idx:	# not water
                    p=pool[c][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])

        elif c==25:	# Patch Triangle Range
            (first,last)=unpack('<HH', h.read(4))
            n=len(v[flags])
            for i in range(n,n+last-first,3):
                if idx:	# not water
                    f[flags].append([i+2,i+1,i])
            for d in range(first,last):
                if idx:	# not water
                    p=pool[curpool][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])
            
        #elif c==26:	# Patch Triangle Strip (not used by DSF2Text)
        #elif c==27:
        #elif c==28:
        
        elif c==29:	# Patch Triangle Fan
            (l,)=unpack('<B', h.read(1))
            n=len(v[flags])
            for i in range(1,l-1):
                if idx:	# not water
                    f[flags].append([n+i+1,n+i,n])
            for i in range(l):
                (d,)=unpack('<H', h.read(2))
                if idx:	# not water
                    p=pool[curpool][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])
            
        elif c==30:	# Patch Triangle Fan - cross-pool
            (l,)=unpack('<B', h.read(1))
            n=len(v[flags])
            for i in range(1,l-1):
                if idx:	# not water
                    f[flags].append([n+i+1,n+i,n])
            for i in range(l):
                (c,d)=unpack('<HH', h.read(4))
                if idx:	# not water
                    p=pool[c][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])

        elif c==31:	# Patch Triangle Fan Range
            (first,last)=unpack('<HH', h.read(4))
            n=len(v[flags])
            for i in range(1,last-first-1):
                if idx:	# not water
                    f[flags].append([n+i+1,n+i,n])
            for d in range(first, last):
                if idx:	# not water
                    p=pool[curpool][d]
                    v[flags].append([(p[0]-centrelon)*onedeg*cos(d2r*p[1]),
                                     (p[1]-centrelat)*onedeg, p[2]])

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
            raise IOError, (c, "Unrecognised command (%d)" % c, path)

    h.close()

    Window.DrawProgressBar(0.99, "Realising")

    water=Material.New("Water")
    water.rgbCol=[0.5, 0.5, 1.0]
    base=Material.New("Base")
    base.rgbCol=[0.5, 1.0, 0.5]
    overlay=Material.New("Overlay")
    overlay.rgbCol=[1.0, 0.5, 0.5]
    materials=[[base,water],[overlay,water]]
    names=['Base','Overlay']
    
    for flags in [0]:	# was [1,0]
        mesh=Mesh.New(names[flags])
        mesh.materials+=materials[flags]
        mesh.mode &= ~(Mesh.Modes.TWOSIDED|Mesh.Modes.AUTOSMOOTH)
        mesh.mode |= Mesh.Modes.NOVNORMALSFLIP
        mesh.verts.extend(v[flags])
        mesh.faces.extend(f[flags])
        mesh.update()

        ob = Object.New("Mesh", names[flags])
        ob.link(mesh)
        Scene.GetCurrent().objects.link(ob)

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


#------------------------------------------------------------------------
def file_callback (filename):
    print "Starting DSF import from " + filename
    Window.WaitCursor(1)
    Window.DrawProgressBar(0, "Importing")
    readDSF(filename)
    Window.DrawProgressBar(1, "Finished")
    Window.RedrawAll()
    Window.WaitCursor(0)
    print "Finished\n"


#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

Window.FileSelector(file_callback,"Import DSF")
