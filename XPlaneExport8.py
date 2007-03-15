#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane v8 Object (.obj)'
Blender: 234
Group: 'Export'
Tooltip: 'Export to X-Plane v8 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.12"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane v8 .obj
format for placement with World-Maker.

Limitations:<br>
  * Only Lamps and Mesh Faces (including "lines") are exported.<br>
  * All faces must share a single texture (this is a limitation of<br>
    the X-Plane .obj file format) apart from cockpit panel faces<br>
    which can additionally use the cockpit panel texture. Multiple<br>
    textures are not automagically merged into one file during the<br>
    export.
"""

#------------------------------------------------------------------------
# X-Plane exporter for blender 2.34 or above
#
# Copyright (c) 2004,2005 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage.
#
# This software is licensed under a Creative Commons License
#   Attribution-ShareAlike 2.0:
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
#   http://creativecommons.org/licenses/by-sa/2.0/legalcode
#
#
# 2005-11-10 v2.10
#  - New file
#
# 2005-11-17 v2.11
#  - Fixed error when ipo exists, but no curve defined.
#  - Added support for updated (hopefully final) Blender 2.40 API.
#  - Fixed bug with translation of child bones.
#

#
# X-Plane renders polygons in scenery files mostly in the order that it finds
# them - it detects use of alpha and deletes wholly transparent polys, but
# doesn't sort by Z-buffer order.
#
# So we have to sort on export to ensure alpha comes after non-alpha. We also
# sort to minimise attribute state changes, in rough order of expense:
#  - HARD - should be first. Renderer merges hard polys with similar non-hard.
#  - TWOSIDE
#  - FLAT
#  - NPOLY - negative so polygon offsets come first
#  - (animations)
#  - PANEL - most expensive
#  - ALPHA - must be last for correctness. Renderer will merge with previous.
#  - (LOD)
#

import sys
import Blender
from Blender import NMesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler
from XPlaneUtils import Vertex, UV
from XPlaneExport import *
#import time

class VT:
    def __init__(self, v, n, uv):
        self.v=v
        self.n=n
        self.uv=uv

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f\t%s" % (self.v, self.n.x, self.n.y,
                                              self.n.z, self.uv)
            
    def equals (self, b):
        return (self.v.equals(b.v) and self.n.equals(b.n) and self.uv.equals(b.uv))

class VLINE:
    def __init__(self, v, c):
        self.v=v
        self.c=c
    
    def __str__ (self):
        return "%s\t%5.2f\t%5.2f\t%5.2f" % (self.v,
                                            round(self.c[0],2),
                                            round(self.c[1],2),
                                            round(self.c[2],2))
    def equals (self, b):
        return (self.v.equals(b.v) and self.c.equals(b.c))

class VLIGHT:
    def __init__(self, v, c):
        self.v=v
        self.c=c

    def __str__ (self):
        return "%s\t%5.2f\t%5.2f\t%5.2f" % (self.v,
                                            round(self.c[0],2),
                                            round(self.c[1],2),
                                            round(self.c[2],2))

    def equals (self, b):
        return (self.v.equals(b.v) and self.c.equals(b.c))

class Prim:
    # Flags in sort order
    HARD=1
    TWOSIDE=2
    FLAT=4
    NPOLY=8
    PANEL=16	# Should be 2nd last
    ALPHA=32	# Must be last
    
    BUCKET1=HARD|TWOSIDE|FLAT|NPOLY
    # ANIM comes here
    BUCKET2=PANEL|ALPHA
    # LOD comes here

    def __init__ (self):
        self.i=[]	# indices for lines & tris, VLIGHT for lights
        self.flags=0
        self.layer=0
        self.anim=None

    def match(self, layer, flags, anim):
        return (self.layer&layer and
                self.flags==flags and
                self.anim.equals(anim))

#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        
        #--- class private don't touch ---
        self.file=None
        self.filename=filename
        self.iscockpit=(('_cockpit.obj' in filename.lower()) or
                        ('_cockpit_inn.obj' in filename.lower()) or
                        ('_cockpit_out.obj' in filename.lower()))
        self.layermask=1
        self.havepanel=False
        self.texture=None
        self.linewidth=0.1
        self.nprim=0		# Number of X-Plane primitives exported

        # attributes controlling export
        self.hard=False
        self.twoside=False
        self.flat=False
        self.npoly=True
        self.panel=False
        self.alpha=False	# implicit - doesn't appear in output file
        self.layer=0
        self.anim=Anim(None)

        # Global vertex lists
        self.vt=[]
        self.vline=[]
        self.anims=[Anim(None)]

        # primitive lists
        self.tris=[]
        self.lines=[]
        self.lights=[]


    #------------------------------------------------------------------------
    def export(self, scene):
        theObjects = []
        theObjects = scene.getChildren()

        print 'Starting OBJ export to ' + self.filename
        if not checkFile(self.filename):
            return

        Blender.Window.WaitCursor(1)
        Window.DrawProgressBar(0, 'Examining textures')
        (self.texture,self.havepanel,self.layermask)=getTexture(theObjects,
                                                                self.layermask,
                                                                self.iscockpit,
                                                                8)
        if self.havepanel:
            self.iscockpit=True
            self.layermask=1
        
        #clock=time.clock()	# Processor time
        frame=Blender.Get('curframe')

        self.file = open(self.filename, 'w')
        self.writeHeader ()
        self.writeObjects (theObjects)
        checkLayers (theObjects, self.iscockpit)
        self.file.close ()
        
        Blender.Set('curframe', frame)
        Window.DrawProgressBar(1, 'Finished')
        #print "%s CPU time" % (time.clock()-clock)
        print "Finished - exported %s primitives\n" % self.nprim

    #------------------------------------------------------------------------
    def writeHeader (self):
        if 'blender.app' in Blender.sys.progname:
            systype='A'
        else:
            systype='I'
        self.file.write("%s\n800\nOBJ\n\n" % systype)
        if self.texture:
            self.file.write("TEXTURE\t\t%s\n" % self.texture)
            l=self.texture.rfind('.')
            if l!=-1 and self.texture[l-3:l].upper()!='LIT':
                self.file.write("TEXTURE_LIT\t%s_LIT%s\n" %(self.texture[:-4],
                                                            self.texture[-4:]))
        else:	# X-Plane barfs if no texture specified
            self.file.write("TEXTURE\t\n")

    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):

        if self.layermask==1:
            lseq=[1]
        else:
            lseq=[1,2,4]

        # Build global vertex lists
        nobj=len(theObjects)
        for o in range (nobj-1,-1,-1):
            object=theObjects[o]
            if not object.Layer&self.layermask:
                continue
            Window.DrawProgressBar(float(nobj-o)/(2*nobj),
                                   "Exporting %d%% ..." % ((nobj-o)*50/nobj))
            objType=object.getType()
            if objType == 'Mesh':
                if isLine(object, self.linewidth):
                    self.sortLine(object)
                else:
                    self.sortMesh(object)
            elif objType in ['Lamp', 'Armature']:
                pass	# these dealt with separately
            else:
                print "Warn:\tIgnoring %s \"%s\"" % (objType.lower(),
                                                     object.name)

        # Lights
        for layer in lseq:
            for o in range (len(theObjects)-1,-1,-1):
                object=theObjects[o]
                if (object.getType()=='Lamp' and object.Layer&layer):
                    self.sortLamp(object)

        # Build ((1+Prim.ALPHA*2) * len(anims) * len(lseq)) indices
        Window.DrawProgressBar(0.5, 'Exporting 50% ...')
        indices=[]
        offsets=[]
        counts=[]
        for layer in lseq:
            for passhi in [0, Prim.PANEL, Prim.ALPHA, Prim.PANEL|Prim.ALPHA]:
                for anim in self.anims:

                    # Lines
                    index=[]
                    offsets.append(len(indices))
                    for line in self.lines:
                        if line.match(layer, passhi, anim):
                            index.append(line.i[0])
                            index.append(line.i[1])
                    counts.append(len(index))
                    indices.extend(index)

                    # Tris
                    # Hack!: Can't have hard tris outside layer 1
                    if layer==2:
                        for tri in self.tris:
                            tri.flags&=~Prim.HARD
                    for passno in range(passhi,passhi+Prim.BUCKET1+1):
                        index=[]
                        offsets.append(len(indices))
                        for tri in self.tris:
                            if tri.match(layer, passno, anim):
                                index.append(tri.i[0])
                                index.append(tri.i[1])
                                index.append(tri.i[2])
                                if len(tri.i)==4:	# quad
                                    index.append(tri.i[0])
                                    index.append(tri.i[2])
                                    index.append(tri.i[3])
                        counts.append(len(index))
                        indices.extend(index)

        self.file.write("POINT_COUNTS\t%d %d %d %d\n\n" % (len(self.vt),
                                                           len(self.vline),
                                                           len(self.lights),
                                                           len(indices)))
        Window.DrawProgressBar(0.6, 'Exporting 60% ...')
        for vt in self.vt:
            self.file.write("VT\t%s\n" % vt)
        if self.vt:
            self.file.write("\n")

        Window.DrawProgressBar(0.7, 'Exporting 70% ...')
        for vline in self.vline:
            self.file.write("VLINE\t%s\n" % vline)
        if self.vline:
            self.file.write("\n")

        for light in self.lights:
            self.file.write("VLIGHT\t%s\n" % light.i)
        if self.lights:
            self.file.write("\n")

        Window.DrawProgressBar(0.8, 'Exporting 80% ...')
        n=len(indices)
        for i in range(0, n-9, 10):
            self.file.write("IDX10\t")
            for j in range(i, i+9):
                self.file.write("%d " % indices[j])
            self.file.write("%d\n" % indices[i+9])
        for j in range(n-(n%10), n):
            self.file.write("IDX\t%d\n" % indices[j])

        # Geometry Commands
        Window.DrawProgressBar(0.9, 'Exporting 90% ...')
        n=0
        for layer in lseq:
            for passhi in [0, Prim.PANEL, Prim.ALPHA, Prim.PANEL|Prim.ALPHA]:
                for anim in self.anims:

                    # Lights
                    i=0
                    while i<len(self.lights):
                        offset=0
                        count=0
                        if self.lights[i].match(layer, passhi, anim):
                            offset=i
                            for j in range(i, len(self.lights)):
                                if not self.lights[j].match(layer,passhi,anim):
                                    count=i-offset
                                    break
                            else:
                                count=len(self.lights)-offset
                            self.updateAttr(0, 0, 0, 1, 0, 0, layer, anim)
                            self.file.write("%sLIGHTS\t%d %d\n" %
                                            (anim.ins(), offset, count))
                            self.nprim+=count
                            i=offset+count
                        else:
                            i=i+1

                    # Lines
                    if counts[n]:
                        self.updateAttr(0, 0, 0, 1, 0, 0, layer, anim)
                        self.file.write("%sLINES\t%d %d\n" %
                                        (anim.ins(), offsets[n], counts[n]))
                        self.nprim+=1
                    n=n+1

                    # Tris
                    for passno in range(passhi,passhi+Prim.BUCKET1+1):
                        if counts[n]:
                            self.updateAttr(passno&Prim.HARD,
                                            passno&Prim.TWOSIDE,
                                            passno&Prim.FLAT,
                                            passno&Prim.NPOLY,
                                            passno&Prim.PANEL,
                                            passno&Prim.ALPHA,
                                            layer, anim)
                            self.file.write("%sTRIS\t%d %d\n" %
                                            (anim.ins(), offsets[n],counts[n]))
                            self.nprim+=counts[n]
                        n=n+1

        # Close animations
        self.updateAttr(self.hard, self.twoside, self.flat, self.npoly,
                        self.panel, self.alpha, self.layer, Anim(None))

        self.file.write("\n# Built with Blender %4.2f. Exported with XPlane2Blender %s.\n" % (float(Blender.Get('version'))/100, __version__))


    #------------------------------------------------------------------------
    def sortLamp(self, object):

        light=Prim()
        (light.anim, mm)=self.makeAnim(object)
        light.layer=object.Layer

        lamp=object.getData()
        name=object.name
        special=0
        
        if lamp.getType() != Lamp.Types.Lamp:
            print "Info:\tIgnoring Area, Spot, Sun or Hemi lamp \"%s\"" % name
            return
        
        if self.verbose:
            print "Info:\tExporting Light \"%s\"" % name

        lname=name.lower()
        c=[0,0,0]
        if 'pulse' in lname:
            c[0]=c[1]=c[2]=9.9
            special=1
        elif 'strobe' in lname:
            c[0]=c[1]=c[2]=9.8
            special=1
        elif 'traffic' in lname:
            c[0]=c[1]=c[2]=9.7
            special=1
        elif 'flash' in lname:
            c[0]=-lamp.col[0]
            c[1]=-lamp.col[1]
            c[2]=-lamp.col[2]
        else:
            c[0]=lamp.col[0]
            c[1]=lamp.col[1]
            c[2]=lamp.col[2]

        light.i=VLIGHT(Vertex(0,0,0, mm), c)
        self.lights.append(light)


    #------------------------------------------------------------------------
    def sortLine(self, object):
        if self.verbose:
            print "Info:\tExporting Line \"%s\"" % object.name

        line=Prim()
        (line.anim, mm)=self.makeAnim(object)
        line.layer=object.Layer

        mesh=object.getData()
        face=mesh.faces[0]

        v=[]
        for i in range(4):
            v.append(Vertex(face.v[i][0],face.v[i][1],face.v[i][2], mm))
        if (v[0].equals(v[1],self.linewidth) and
            v[2].equals(v[3],self.linewidth)):
            i=0
        else:
            i=1
        v1=Vertex((v[i].x+v[i+1].x)/2,
                  (v[i].y+v[i+1].y)/2,
                  (v[i].z+v[i+1].z)/2)
        v2=Vertex((v[i+2].x+v[(i+3)%4].x)/2,
                  (v[i+2].y+v[(i+3)%4].y)/2,
                  (v[i+2].z+v[(i+3)%4].z)/2)

        if len(mesh.materials)>face.mat:
            c=[mesh.materials[face.mat].R,
               mesh.materials[face.mat].G,
               mesh.materials[face.mat].B,]
        else:
            c=[0.5,0.5,0.5]

        for v in [v1,v2]:
            vline=VLINE(v, c)

            for j in range(len(self.vline)):
                q=self.vline[j]
                if vline.equals(q):
                    line.i.append(j)
                    break
            else:
                j=len(self.vline)
                self.vline.append(vline)
                line.i.append(j)

        self.lines.append(line)


    #------------------------------------------------------------------------
    def sortMesh(self, object):

        nmesh=object.getData()
        
        (anim, mm)=self.makeAnim(object)
        nm=mm.rotationPart()
        nm.resize4x4()

        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
                
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(nmesh.faces))

        # Build list of faces and vertices
        twosideerr=0
        harderr=0
        vti = [[] for i in range(len(nmesh.verts))]
        
        for f in nmesh.faces:
            n=len(f.v)
            if not n in [3,4]:
                if self.verbose:
                    print "Warn:\tIgnoring degenerate face in mesh \"%s\"" % (
                        object.name)
            elif not (f.mode & NMesh.FaceModes.INVISIBLE):
                face=Prim()
                face.anim=anim
                face.layer=object.Layer
   
                if f.mode & NMesh.FaceModes.TEX:
                    if len(f.uv)!=n:
                        raise ExportError("Missing UV in mesh \"%s\"" % object.name)
                    if f.transp == NMesh.FaceTranspModes.ALPHA:
                        face.flags|=Prim.ALPHA

                if f.mode & NMesh.FaceModes.TWOSIDE:
                    face.flags|=Prim.TWOSIDE
                    twosideerr=twosideerr+1

                if not f.smooth:
                    face.flags|=Prim.FLAT

                if not f.mode & NMesh.FaceModes.TILES:
                    face.flags|=Prim.NPOLY
                    
                if f.image and 'panel.' in f.image.name.lower():
                    face.flags|=Prim.PANEL
                elif not (f.mode&NMesh.FaceModes.DYNAMIC or self.iscockpit):
                    face.flags|=Prim.HARD
                    harderr=harderr+1

                for i in range(n-1,-1,-1):
                    nmv=f.v[i]
                    vertex=Vertex(nmv[0], nmv[1], nmv[2], mm)
                    if face.flags&Prim.FLAT:
                        norm=Vertex(f.no, nm)
                    else:
                        norm=Vertex(nmv.no, nm)
                    if f.mode & NMesh.FaceModes.TEX:
                        uv=UV(f.uv[i][0], f.uv[i][1])
                    else:	# File format requires something - using (0,0)
                        uv=UV(0,0)
                    vt=VT(vertex, norm, uv)

                    # Does one already exist?
                    #for j in range(len(self.vt)):	# Search all meshes
                    for j in vti[nmv.index]:		# Search only this mesh
                        q=self.vt[j]
                        if vt.equals(q):
                            q.uv= (q.uv+ vt.uv)/2
                            face.i.append(j)
                            break
                    else:
                        j=len(self.vt)
                        self.vt.append(vt)
                        face.i.append(j)
                        vti[nmv.index].append(j)

                self.tris.append(face)
                
                #if self.debug: print face

        if harderr:
            print "Info:\tFound %s hard face(s) in mesh \"%s\"" % (
                harderr, object.name)
        if twosideerr:
            print "Info:\tFound %s two-sided face(s) in mesh \"%s\"" % (
                twosideerr, object.name)


    #------------------------------------------------------------------------
    # Return (Anim object, Transformation for object relative to world/parent)
    def makeAnim(self, child):

        #return (Anim(None), mm)	# test - return frame 1 position

        anim=Anim(child)

        # Add parent anims first
        al=[]
        a=anim
        while not a.equals(Anim(None)):
            al.insert(0, a)
            a=a.anim

        Blender.Set('curframe', 1)
        #mm=Matrix(child.getMatrix('localspace')) doesn't work in 2.40a1&2
        mm=child.getMatrix('worldspace')
        
        for a in al:
            # Hack!
            # We need the position of the child in bone space - ie
            # rest position relative to bone root.
            # child.getMatrix('localspace') doesn't return this in 2.40a1&2.
            # So un-apply animation from child's worldspace in frame 1:
            #  - get child in worldspace in frame 1 (mm)
            #  - translate so centre of rotation is at origin (-bone root)
            #  - unrotate (-pose rotation)
            
            if self.debug:
                print "pre\t%s" % mm.rotationPart().toEuler()
                print "\t%s" % mm.translationPart()

            # anim is in X-Plane space. But we need Blender space. Yuck.
            mm=Matrix(mm[0],mm[1],mm[2],
                      mm[3]-Vector([a.t[0].x, -a.t[0].z, a.t[0].y, 0]))

            if a.r and a.a[0]:
                tr=RotationMatrix(a.a[0], 4, 'r',
                                  -Vector([a.r[0].x, -a.r[0].z, a.r[0].y]))
                mm=mm*tr
                if self.debug:
                    print "rot\t%s" % tr.rotationPart().toEuler()

            if self.debug:
                print "post\t%s" % mm.rotationPart().toEuler()
                print "\t%s" % mm.translationPart()

            # Add Anim, but avoid dups
            for b in self.anims:
                if a.equals(b):
                    anim=b
                    break
            else:
                self.anims.append(a)
                anim=a	# The anim we just made is the last one in the list

        return (anim, mm)


    #------------------------------------------------------------------------
    def updateAttr(self, hard, twoside, flat, npoly, panel, alpha, layer,anim):

        if layer!=self.layer:
            # Reset all attributes
            while not self.anim.equals(Anim(None)):
                self.anim=self.anim.anim
                self.file.write("%sANIM_end\n" % self.anim.ins())
            self.hard=False
            self.twoside=False
            self.flat=False
            self.npoly=True
            self.panel=False
            self.alpha=False
                
            if self.layermask==1:
                self.file.write("\n")
            else:
                if layer==1:
                    self.file.write("\nATTR_LOD\t0 1000\n")
                elif layer==2:
                    self.file.write("\nATTR_LOD\t1000 4000\n")
                else:
                    self.file.write("\nATTR_LOD\t4000 10000\n")
            self.layer=layer

        if not anim.equals(self.anim):
            olda=[]
            newa=[]
            a=self.anim
            while not a.equals(Anim(None)):
                olda.insert(0, a)
                a=a.anim
            a=anim
            while not a.equals(Anim(None)):
                newa.insert(0, a)
                a=a.anim
            for i in range(len(olda)-1,-1,-1):
                if i>=len(newa) or not newa[i].equals(olda[i]):
                    olda.pop()
                    self.anim=self.anim.anim
                    self.file.write("%sANIM_end\n" % self.anim.ins())
            for i in newa[len(olda):]:
                self.file.write("%sANIM_begin\n" % self.anim.ins())
                self.anim=i
                if not (self.anim.t[0].equals(Vertex(0,0,0)) and
                        self.anim.t[1].equals(Vertex(0,0,0))):
                    self.file.write("%sANIM_trans\t%s\t%s\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.t[0], self.anim.t[1],
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                if len(self.anim.r)==1:
                    self.file.write("%sANIM_rotate\t%s\t%7.2f %7.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[0],
                        self.anim.a[0], self.anim.a[1],
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                elif len(self.anim.r)==2:
                    self.file.write("%sANIM_rotate\t%s\t%7.2f %7.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[0],
                        self.anim.a[0], 0,
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                    self.file.write("%sANIM_rotate\t%s\t%7.2f %7.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[1],
                        0, self.anim.a[1],
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                        

        # For readability, write turn-offs before turn-ons

        if self.hard and not hard:
            self.file.write("%sATTR_no_hard\n" % self.anim.ins())

        if self.twoside and not twoside:
            self.file.write("%sATTR_cull\n" % self.anim.ins())

        if self.flat and not flat:
            self.file.write("%sATTR_shade_smooth\n" % self.anim.ins())

        if self.npoly and not npoly:
            self.file.write("%sATTR_poly_os\t2\n" % self.anim.ins())

        if self.panel and not panel:
            self.file.write("%sATTR_no_cockpit\n" % self.anim.ins())

        # alpha is implicit - doesn't appear in output file
        if self.alpha and not alpha:
            self.file.write("%s####_no_alpha\n" % self.anim.ins())

        # Turn Ons
        if hard and not self.hard:
            self.file.write("%sATTR_hard\n" % self.anim.ins())

        if twoside and not self.twoside:
            self.file.write("%sATTR_no_cull\n" % self.anim.ins())

        if flat and not self.flat:
            self.file.write("%sATTR_shade_flat\n" % self.anim.ins())

        if npoly and not self.npoly:
            self.file.write("%sATTR_poly_os\t0\n" % self.anim.ins())

        if panel and not self.panel:
            self.file.write("%sATTR_cockpit\n" % self.anim.ins())

        # alpha is implicit - doesn't appear in output file
        if alpha and not self.alpha:
            self.file.write("%s####_alpha\n" % self.anim.ins())

        self.hard=hard
        self.twoside=twoside
        self.flat=flat
        self.npoly=npoly
        self.panel=panel
        self.alpha=alpha


#------------------------------------------------------------------------
class Anim:
    # From http://www.xsquawkbox.net/xpsdk/docs/DataRefs.html
    # Datarefs for X-Plane 820, compiled Fri Oct 07 10:52:16 2005
    refs=[('sim/aircraft/view/',
           ['acf_size_x',
            'acf_size_z',
            'acf_HUD_type',
            'acf_asi_kts',
            'acf_cockpit_type',
            'acf_has_SC_fd',
            'acf_has_stallwarn',
            'acf_has_litemap_tex',
            'acf_peX',
            'acf_peY',
            'acf_peZ',
            'acf_Vso',
            'acf_Vs',
            'acf_Vfe',
            'acf_Vno',
            'acf_Vne',
            'acf_Mmo',
            'acf_Gneg',
            'acf_Gpos',
            'acf_est_Vs',
            'acf_yawstringx',
            'acf_yawstringy',
            'acf_HUD_cntrx',
            'acf_HUD_cntry',
            'acf_HUD_delx',
            'acf_HUD_dely',
            'acf_has_lanlite1',
            'acf_lanlite1X',
            'acf_lanlite1Y',
            'acf_lanlite1Z',
            'acf_lanlite_the',
            'acf_has_lanlite2',
            'acf_lanlite2X',
            'acf_lanlite2Y',
            'acf_lanlite2Z',
            'acf_has_lanlite3',
            'acf_lanlite3X',
            'acf_lanlite3Y',
            'acf_lanlite3Z',
            'acf_has_fuserb1',
            'acf_fuserb1X',
            'acf_fuserb1Y',
            'acf_fuserb1Z',
            'acf_has_fuserb2',
            'acf_fuserb2X',
            'acf_fuserb2Y',
            'acf_fuserb2Z',
            'acf_has_taillite',
            'acf_tailliteX',
            'acf_tailliteY',
            'acf_tailliteZ',
            'acf_has_navlites']),
          ('sim/aircraft/panel/',
           ['acf_ins_type',
            'acf_ins_size',
            'acf_ins_x',
            'acf_ins_y',
            'acf_ins_delx',
            'acf_ins_dely']),
          ('sim/aircraft/forcefeedback/',
           ['acf_ff_hydraulic',
            'acf_ff_stickshaker']),
          ('sim/aircraft/engine/',
           ['acf_num_engines',
            'acf_auto_featherEQ',
            'acf_throtmax_FWD',
            'acf_throtmax_REV',
            'acf_RSC_idlespeed_eng',
            'acf_RSC_redline_eng',
            'acf_RSC_mingreen_eng',
            'acf_RSC_maxgreen_eng',
            'acf_pmax',
            'acf_tmax',
            'acf_burnerinc',
            'acf_critalt',
            'acf_mpmax',
            'acf_gear_rat',
            'acf_face_jet',
            'acf_face_rocket',
            'acf_spooltime_jet',
            'acf_max_mach_eff',
            'acf_fmax_sl',
            'acf_fmax_opt',
            'acf_fmax_vac',
            'acf_h_opt',
            'aacf_tip_mach_des_50',
            'aacf_tip_mach_des_100',
            'aacf_rotor_mi_rat',
            'aacf_tip_weight',
            'acf_max_ITT',
            'acf_max_EGT',
            'acf_max_CHT',
            'acf_max_OILP',
            'acf_max_OILT',
            'acf_max_FUELP']),
          ('sim/aircraft/prop/',
           ['acf_en_type',
            'acf_revthrust_eq',
            'acf_prop_type',
            'acf_prop_gear_rat',
            'acf_prop_dir',
            'acf_num_blades',
            'acf_SFC',
            'acf_min_pitch',
            'acf_max_pitch',
            'acf_reversed_pitch',
            'acf_sidecant',
            'acf_vertcant',
            'acf_prop_mass',
            'acf_miprop_rpm',
            'acf_discarea',
            'acf_ringarea',
            'acf_bladesweep',
            'acf_des_rpm_prp',
            'acf_des_kts_prp',
            'acf_des_kts_acf',
            'acf_part_eq']),
          ('sim/aircraft/parts/',
           ['acf_els',
            'acf_Xarm',
            'acf_Yarm',
            'acf_Zarm',
            'acf_X_body_aero',
            'acf_Y_body_aero',
            'acf_Z_body_aero',
            'acf_Croot',
            'acf_Ctip',
            'acf_dihed1',
            'acf_sweep1',
            'acf_sweep2',
            'acf_sweepnow',
            'acf_varsweepEQ',
            'acf_semilen_SEG',
            'acf_semilen_JND',
            'acf_e',
            'acf_AR',
            'acf_al_D_al0',
            'acf_cl_D_cl0',
            'acf_cm_D_cm0',
            'acf_delta_fac',
            'acf_spec_wash',
            'acf_alpha_max',
            'acf_slat_effect',
            'acf_s',
            'acf_mac',
            'acf_anginc',
            'acf_ail1',
            'acf_ail2',
            'acf_splr',
            'acf_flap',
            'acf_flap2',
            'acf_flapEQ',
            'acf_slat',
            'acf_slatEQ',
            'acf_sbrk',
            'acf_sbrkEQ',
            'acf_drud',
            'acf_elev',
            'acf_rudd',
            'acf_rudd2',
            'acf_in_downwash',
            'acf_body_r',
            'acf_gear_type',
            'acf_gear_latE',
            'acf_gear_lonE',
            'acf_gear_axiE',
            'acf_gear_latR',
            'acf_gear_lonR',
            'acf_gear_axiR',
            'acf_gear_latN',
            'acf_gear_lonN',
            'acf_gear_axiN',
            'acf_gear_leglen',
            'acf_gear_tirrad',
            'acf_gearcon',
            'acf_geardmp',
            'acf_gearstatdef',
            'acf_gear_def',
            'acf_gear_deploy',
            'acf_gear_xnodef',
            'acf_gear_ynodef',
            'acf_gear_znodef']),
          ('sim/aircraft/bodies/',
           ['acf_fuse_cd',
            'acf_fuse_cd_array']),
          ('sim/aircraft/controls/',
           ['acf_ail1_crat',
            'acf_ail1_up',
            'acf_ail1_dn',
            'acf_RSC_idlespeed_prp',
            'acf_RSC_redline_prp',
            'acf_ail2_crat',
            'acf_ail2_up',
            'acf_ail2_dn',
            'acf_RSC_mingreen_prp',
            'acf_RSC_maxgreen_prp',
            'acf_elev_crat',
            'acf_elev_up',
            'acf_elev_dn',
            'acf_trq_max_eng',
            'acf_trq_max_prp',
            'acf_rudd_crat',
            'acf_rudd_lr',
            'acf_rud2_crat',
            'acf_rud2_lr',
            'acf_splr_crat',
            'acf_splr_up',
            'acf_sbrk_crat',
            'acf_sbrk_up',
            'acf_flap_crat',
            'acf_flap2_crat',
            'acf_flap_dn',
            'acf_flap2_dn',
            'acf_hstb_trim_up',
            'acf_hstb_trim_dn',
            'acf_flap_type',
            'acf_flap2_type',
            'acf_con_smooth',
            'acf_flap_cl',
            'acf_flap_cd',
            'acf_flap_cm',
            'acf_flap2_cl',
            'acf_flap2_cd',
            'acf_flap2_cm',
            'acf_flap_detents',
            'acf_flap_deftime',
            'acf_slat_inc',
            'acf_blown_flap_add_speed',
            'acf_blown_flap_throt_red',
            'acf_blown_flap_min_engag']),
          ('sim/aircraft/gear/',
           ['acf_gear_retract',
            'acf_is_taildragger',
            'acf_gear_is_skid',
            'acf_nw_steerdeg1',
            'acf_nw_steerdeg2',
            'acf_nw_cutoff_speed',
            'acf_water_rud_longarm',
            'acf_water_rud_area',
            'acf_water_rud_maxdef',
            'acf_h_eqlbm',
            'acf_the_eqlbm',
            'acf_gear_door_typ',
            'acf_gear_door_loc',
            'acf_gear_door_geo',
            'acf_gear_door_axi_rot',
            'acf_gear_door_ext_ang',
            'acf_gear_door_ret_ang',
            'acf_gear_door_ang_now']),
          ('sim/aircraft/weight/',
           ['acf_cgY',
            'acf_cgZ',
            'acf_Jxx_unitmass',
            'acf_Jyy_unitmass',
            'acf_Jzz_unitmass',
            'acf_m_empty',
            'acf_m_displaced',
            'acf_m_max',
            'acf_m_fuel_tot',
            'acf_m_jettison',
            'acf_m_displaced_y']),
          ('sim/aircraft/specialcontrols/',
           ['acf_jato_theta',
            'acf_jato_thrust',
            'acf_jato_dur',
            'acf_jato_sfc',
            'acf_jato_Y',
            'acf_jato_Z',
            'acf_brake_area',
            'acf_brake_Y',
            'acf_brake_Z',
            'acf_chute_area',
            'acf_chute_Y',
            'acf_chute_Z',
            'acf_ail1pitch',
            'acf_ail1flaps',
            'acf_ail2pitch',
            'acf_ail2flaps',
            'acf_stabroll',
            'acf_stabhdng',
            'acf_ail2vmax',
            'acf_tvec_ptch',
            'acf_tvec_roll',
            'acf_tvec_hdng',
            'acf_diff_thro_with_hdng',
            'acf_arrestingEQ',
            'acf_antiiceEQ',
            'acf_warn1EQ',
            'acf_gearhornEQ',
            'acf_autosbrkEQ',
            'acf_autofbrkEQ',
            'acf_autosweepEQ',
            'acf_autoslatEQ']),
          ('sim/aircraft/vtolcontrols/',
           ['acf_vectEQ',
            'acf_vectarmZ',
            'acf_cyclic_elev',
            'acf_cyclic_ailn',
            'acf_delta3',
            'acf_puffL',
            'acf_puffM',
            'acf_puffN',
            'acf_tail_with_coll',
            'acf_diff_coll_with_roll',
            'acf_diff_coll_with_hdng',
            'acf_diff_cycl_with_hdng_lon',
            'acf_auto_rpm_with_tvec',
            'acf_rotor_trim_max_fwd',
            'acf_rotor_trim_max_aft']),
          ('sim/aircraft/artstability/',
           ['acf_AShiV',
            'acf_ASloV',
            'acf_ASmaxp_lo',
            'acf_ASp_lo_rate',
            'acf_ASmaxp_hi',
            'acf_ASp_hi_pos',
            'acf_ASmaxh_lo',
            'acf_ASh_lo_rate',
            'acf_ASmaxh_hi',
            'acf_ASh_hi_pos',
            'acf_ASmaxr_lo',
            'acf_ASr_lo_rate',
            'acf_ASmaxr_hi',
            'acf_ASr_hi_rate',
            'acf_has_clutch',
            'acf_has_idlespeed']),
          ('sim/aircraft/overflow/',
           ['acf_element_len',
            'acf_gear_door_size',
            'acf_stab_delinc_to_Vne',
            'acf_Vmca',
            'acf_Vyse',
            'acf_flap_arm',
            'acf_cgZ_fwd',
            'acf_cgZ_aft',
            'acf_gear_cyc_time',
            'acf_refuel_X',
            'acf_refuel_Y',
            'acf_refuel_Z',
            'acf_gear_steers',
            'acf_hybrid_gear',
            'acf_vardihedEQ',
            'acf_dihed2',
            'acf_dihednow',
            'jett_X',
            'jett_Y',
            'jett_Z',
            'acf_puffX',
            'acf_puffY',
            'acf_puffZ',
            'acf_Vle',
            'acf_ASp_hi_rate',
            'acf_ASh_hi_rate',
            'acf_spooltime_prop',
            'acf_elevflaps',
            'acf_tank_X',
            'acf_tank_Y',
            'acf_tank_Z',
            'acf_tank_rat',
            'acf_stall_warn_alpha',
            'acf_mass_shift',
            'acf_mass_shift_dx',
            'acf_mass_shift_dz',
            'acf_feathered_pitch',
            'acf_ASmaxg_hi',
            'acf_ASg_hi_pos',
            'acf_ASg_hi_rate',
            'acf_wing_tilt_ptch',
            'acf_wing_tilt_roll',
            'acf_max_press_diff',
            'acf_diff_coll_with_ptch',
            'acf_flap_roll',
            'acf_flap_ptch',
            'acf_lift_fan_rat',
            'acf_diff_cycl_with_hdng_lat',
            'acf_phase_tvect_out_at_90',
            'acf_roll_co',
            'acf_brake_co',
            'acf_drive_by_wire',
            'acf_is_glossy',
            'acf_num_tanks',
            'acf_has_refuel',
            'acf_draw_geo_frnt_views',
            'acf_draw_geo_side_views',
            'acf_jett_is_slung',
            'acf_eng_mass',
            'acf_phase_tvect_out_at_00',
            'acf_auto_trimEQ',
            'acf_has_DC_fd',
            'acf_flaps_with_gearEQ',
            'acf_rev_on_touchdown',
            'acf_flaps_with_vecEQ',
            'acf_blow_all_controls',
            'acf_warn2EQ',
            'acf_num_thrustpoints',
            'acf_props_linked',
            'acf_Xwpn_att',
            'acf_Ywpn_att',
            'acf_Zwpn_att',
            'acf_cus_rnd_use',
            'acf_cus_rnd_lo_val',
            'acf_cus_rnd_hi_val',
            'acf_cus_rnd_lo_ang',
            'acf_cus_rnd_hi_ang',
            'acf_has_nav',
            'acf_has_radar',
            'acf_has_beta',
            'acf_cus_rnd_mirror',
            'acf_cus_rnd_label',
            'acf_cus_dig_use',
            'acf_cus_dig_offset',
            'acf_cus_dig_scale',
            'acf_cus_dig_dig',
            'acf_cus_dig_dec',
            'acf_inc_ail',
            'acf_inc_ail2',
            'acf_inc_vec',
            'acf_tow_hook_Y',
            'acf_tow_hook_Z',
            'acf_win_hook_Y',
            'acf_win_hook_Z',
            'acf_nosewheel_k',
            'acf_vectarmY',
            'acf_hide_prop_at_90_vect']),
          ('sim/airfoils/',
           ['afl_clB',
            'afl_Lpow',
            'afl_Lstall',
            'afl_Ldrop1',
            'afl_Lpowstl',
            'afl_Ldrop2',
            'afl_Dmin',
            'afl_DminCL',
            'afl_Dal10',
            'afl_Dpow',
            'afl_Bloc',
            'afl_Bwidth',
            'afl_Bdepth',
            'afl_Bpower',
            'afl_cmal2',
            'afl_cmal3',
            'afl_cm1',
            'afl_cm2',
            'afl_cm3',
            'afl_cm4',
            'afl_almin',
            'afl_almax',
            'afl_almin_array',
            'afl_almax_array',
            'afl_re_num',
            'afl_t_rat',
            'afl_mach_div',
            'afl_clM',
            'afl_cl',
            'afl_cd',
            'afl_cm']),
          ('sim/cockpit/autopilot/',
           ['autopilot_mode',
            'airspeed_mode',
            'heading_mode',
            'altitude_mode',
            'backcourse_on',
            'approach_selector',
            'altitude',
            'current_altitude',
            'vertical_velocity',
            'airspeed',
            'heading',
            'heading_mag',
            'heading_mag2',
            'airspeed_is_mach',
            'flight_director_pitch',
            'flight_director_roll',
            'autopilot_state',
            'heading_roll_mode',
            'mode_hnav',
            'mode_gls',
            'alt_hold_ft_fms',
            'syn_hold_deg']),
          ('sim/cockpit/electrical/',
           ['battery_on',
            'battery_array_on',
            'battery_EQ',
            'avionics_on',
            'avionics_EQ',
            'generator_on',
            'generator_EQ',
            'HUD_on',
            'HUD_brightness',
            'beacon_lights_on',
            'landing_lights_on',
            'nav_lights_on',
            'strobe_lights_on',
            'taxi_light_on',
            'cockpit_lights_on',
            'cockpit_lights',
            'instrument_brightness',
            'sunglasses_on',
            'night_vision_on',
            'ah_bar']),
          ('sim/cockpit/engine/',
           ['inverter_on',
            'inverter_eq',
            'fuel_pump_on',
            'fuel_pump_EQ',
            'fadec_on',
            'idle_speed',
            'fuel_tank_selector',
            'fuel_tank_transfer',
            'fuel_tank_transfer_from',
            'ignition_on',
            'igniters_on',
            'starter_duration',
            'clutch_engage',
            'APU_switch',
            'APU_running',
            'APU_N1']),
          ('sim/cockpit/gps/',
           ['course',
            'destination_type',
            'destination_index',
            'airport_index',
            'vor_index',
            'ndb_index',
            'fix_index']),
          ('sim/cockpit/gyros/',
           ['the_vac_ind_deg',
            'psi_vac_ind_degm',
            'phi_vac_ind_deg',
            'the_ele_ind_deg',
            'psi_ele_ind_degm',
            'phi_ele_ind_deg',
            'dg_drift_vac_deg',
            'dg_drift_ele_deg'
            'gyr_force',
            'gyr_spin']),
          ('sim/cockpit/misc/',
           ['has_radar',
            'outer_marker_lit',
            'middle_marker_lit',
            'inner_marker_lit',
            'barometer_setting',
            'barometer_setting2',
            'radio_altimeter_minimum',
            'show_path',
            'vacuum',
            'vacuum2',
            'ah_adjust']),
          ('sim/cockpit/pressure/',
           ['bleed_air_on',
            'bleed_air_mode',
            'cabin_altitude_set_m_msl',
            'cabin_vvi_set_m_msec',
            'cabin_altitude_actual_m_msl',
            'cabin_vvi_actual_m_msec',
            'pressure_test_timeout',
            'max_allowable_altitude',
            'dump_all',
            'dump_to_alt']),
          ('sim/cockpit/radios/',
           ['nav1_freq_hz',
            'nav2_freq_hz',
            'com1_freq_hz',
            'com2_freq_hz',
            'adf1_freq_hz',
            'adf2_freq_hz',
            'dme_freq_hz',
            'nav1_stdby_freq_hz',
            'nav2_stdby_freq_hz',
            'com1_stdby_freq_hz',
            'com2_stdby_freq_hz',
            'adf1_stdby_freq_hz',
            'adf2_stdby_freq_hz',
            'dme_stdby_freq_hz',
            'nav1_obs_degt',
            'nav2_obs_degt',
            'adf1_obs_card',
            'adf2_obs_card',
            'nav1_obs_degm',
            'nav1_obs_degm2',
            'nav2_obs_degm',
            'nav2_obs_degm2',
            'adf1_obs_card_mag',
            'adf2_obs_card_mag',
            'nav1_dir_degt',
            'nav2_dir_degt',
            'adf1_dir_degt',
            'adf2_dir_degt',
            'gps_dir_degt',
            'dme_dir_degt',
            'nav1_hdef_deg',
            'nav2_hdef_deg',
            'gps_hdef_deg',
            'nav1_hdef_dot',
            'nav1_hdef_dot2',
            'nav2_hdef_dot',
            'nav2_hdef_dot2',
            'gps_hdef_dot',
            'gps_hdef_dot2',
            'nav1_vdef_deg',
            'nav2_vdef_deg',
            'gps_vdef_deg',
            'nav1_vdef_dot',
            'nav1_vdef_dot2',
            'nav2_vdef_dot',
            'nav2_vdef_dot2',
            'gps_vdef_dot',
            'gps_vdef_dot2',
            'nav1_fromto',
            'nav1_fromto2',
            'nav2_fromto',
            'nav2_fromto2',
            'gps_fromto',
            'gps_fromto2',
            'nav1_gls_flag',
            'nav2_gls_flag',
            'nav1_CDI',
            'nav2_CDI',
            'nav1_dme_dist_m',
            'nav2_dme_dist_m',
            'adf1_dme_dist_m',
            'adf2_dme_dist_m',
            'gps_dme_dist_m',
            'standalone_dme_dist_m',
            'nav1_dme_speed_kts',
            'nav2_dme_speed_kts',
            'adf1_dme_speed_kts',
            'adf2_dme_speed_kts',
            'gps_dme_speed_kts',
            'standalone_dme_speed_kts',
            'nav1_dme_time_secs',
            'nav2_dme_time_secs',
            'adf1_dme_time_secs',
            'adf2_dme_time_secs',
            'gps_dme_time_secs',
            'standalone_dme_time_secs',
            'nav1_course_degt',
            'nav1_course_degt2',
            'nav2_course_degt',
            'nav2_course_degt2',
            'gps_course_degt',
            'gps_course_degt2',
            'nav1_course_degm',
            'nav1_course_degm2',
            'nav2_course_degm',
            'nav2_course_degm2',
            'gps_course_degtm',
            'gps_course_degtm2',
            'nav1_slope_degt',
            'nav2_slope_degt',
            'transponder_code',
            'transponder_id',
            'transponder_light',
            'transponder_brightness',
            'transponder_mode',
            'nav1_cardinal_dir',
            'nav1_cardinal_dir2',
            'nav2_cardinal_dir',
            'nav2_cardinal_dir2',
            'adf1_cardinal_dir',
            'adf1_cardinal_dir2',
            'adf2_cardinal_dir',
            'adf2_cardinal_dir2',
            'vac_start_time',
            'vac_stop_time',
            'nav1_has_dme',
            'nav2_has_dme',
            'adf1_has_dme',
            'adf2_has_dme',
            'dme5_has_dme',
            'obs_mag',
            'gear_audio_working',
            'marker_audio_working',
            'nav_type',
            'ap_src']),
          ('sim/cockpit/switches/',
           ['DME_radio_selector',
            'DME_distance_or_time',
            'HSI_selector',
            'HSI_selector2',
            'RMI_selector',
            'RMI_selector2',
            'RMI_l_vor_adf_selector',
            'RMI_l_vor_adf_selector2',
            'RMI_r_vor_adf_selector',
            'RMI_r_vor_adf_selector2',
            'EFIS_dme_1_selector',
            'EFIS_dme_2_selector',
            'marker_panel_out',
            'audio_panel_out',
            'pitot_heat_on',
            'pitot_heat_on2',
            'anti_ice_on',
            'anti_ice_auto_ignite',
            'anti_ice_inert_sep',
            'anti_ice_inlet_heat',
            'anti_ice_prop_heat',
            'anti_ice_surf_heat',
            'anti_ice_surf_boot',
            'anti_ice_window_heat',
            'anti_ice_AOA_heat',
            'auto_brake_settings',
            'auto_feather_mode',
            'auto_fea_EQ',
            'yaw_damper_on',
            'art_stab_on',
            'pre_rotating',
            'pre_rotate_level',
            'parachute_on',
            'jato_on',
            'prop_sync_on',
            'puffers_on',
            'water_scoop',
            'arresting_gear',
            'dumping_fuel',
            'tot_ener_audio',
            'EFIS_map_mode',
            'EFIS_map_submode',
            'EFIS_map_range_selector',
            'ECAM_mode',
            'gear_handle_status',
            'EFIFS_shows_weather',
            'EFIS_shows_tcas',
            'EFIS_shows_airports',
            'EFIS_shows_waypoints',
            'EFIS_shows_VORs',
            'EFIS_shows_NDBs',
            'HITS_mode',
            'argus_mode']),
          ('sim/cockpit/warnings/',
           ['ECAM_warning_on',
            'warning_suppression_timeout',
            'master_caution_timeout',
            'master_caution_on',
            'master_accept_on',
            'annunciator_test_timeout']),
          ('sim/cockpit/warnings/annunciators/',
           ['master_caution',
            'master_warning',
            'master_accept',
            'autopilot_disconnect',
            'low_vacuum',
            'low_voltage',
            'fuel_quantity',
            'hydraulic_pressure',
            'fuel_pressure',
            'oil_pressure',
            'oil_temperature',
            'inverter',
            'generator',
            'chip_detect',
            'engine_fire',
            'auto_ignition',
            'speedbrake',
            'GPWS',
            'ice',
            'lo_rotor',
            'hi_rotor',
            'reverse']),
          ('sim/cockpit/weapons/',
           ['guns_armed',
            'rockets_armed',
            'missiles_armed',
            'bombs_armed',
            'firing_mode',
            'firing_rate',
            'plane_target_index']),
          ('sim/cockpit/avidyne/',
           ['lft_hil',
            'rgt_hil',
            'alt_hil',
            'src',
            'hsi_mode',
            'map_range_sel']),
          ('sim/flightmodel/controls/',
           ['sbrkrat',
            'flaprqst',
            'slatrqst',
            'ail_trim',
            'dist',
            'elv_trim',
            'flaprat',
            'flap2rat',
            'l_brake_add',
            'r_brake_add',
            'lail1def',
            'lail2def',
            'rail1def',
            'rail2def',
            'ldruddef',
            'rdruddef',
            'lsplrdef',
            'rsplrdef',
            'ail1_def',
            'ail2_def',
            'splr_def',
            'splr2_def',
            'yawb_def',
            'rudd_def',
            'rudd2_def',
            'elv1_def',
            'elv2_def',
            'fla1_def',
            'fla2_def',
            'sbrkrqst',
            'vectrqst',
            'swdi',
            'swdirqst',
            'slatrat',
            'nosewheel_steer',
            'parkbrake',
            'rot_trim',
            'rud_trim',
            'incid_rqst',
            'dihed_rqst',
            'vect_rat',
            'incid_rat',
            'dihed_rat']),
          ('sim/flightmodel/cyclic/',
           ['cyclic_ailn_blad_alph',
            'cyclic_ailn_disc_tilt',
            'cyclic_elev_blad_alph',
            'cyclic_elev_disc_tilt',
            'cyclic_elev_command',
            'cyclic_ailn_command',
            'sidecant',
            'vertcant',
            'disc_ang']),
          ('sim/flightmodel/engine/',
           ['ENGN_N2_',
            'ENGN_EGT',
            'ENGN_ITT',
            'ENGN_CHT',
            'ENGN_EGT_c',
            'ENGN_ITT_c',
            'ENGN_CHT_c',
            'ENGN_bat_amp',
            'ENGN_bat_volt',
            'ENGN_cowl',
            'ENGN_EPR',
            'ENGN_FF_',
            'ENGN_gen_amp',
            'ENGN_heat',
            'ENGN_mixt',
            'ENGN_MPR',
            'ENGN_N1_',
            'ENGN_oil_press_psi',
            'ENGN_oil_temp_c',
            'ENGN_oil_press',
            'ENGN_oil_temp',
            'ENGN_power',
            'ENGN_prop',
            'ENGN_sigma',
            'ENGN_thro',
            'ENGN_thro_use',
            'ENGN_thro_override',
            'ENGN_TRQ',
            'ENGN_running',
            'ENGN_burning',
            'ENGN_propmode',
            'ENGN_burnrat',
            'ENGN_oil_quan',
            'ENGN_mixt_pow_rat',
            'ENGN_oil_lube_rat',
            'ENGN_crbice',
            'ENGN_tacrad',
            'ENGN_omegadot',
            'POINT_pitch_deg',
            'POINT_prop_eff',
            'POINT_tacrad',
            'POINT_thrust',
            'POINT_rock_TRQ',
            'POINT_drag_TRQ',
            'POINT_omegadot',
            'POINT_cone_rad',
            'POINT_side_wash',
            'POINT_XYZ',
            'POINT_pitch_deg_use']),
          ('sim/flightmodel/failures/',
           ['frm_ice',
            'pitot_ice',
            'pitot_ice2',
            'prop_ice',
            'inlet_ice',
            'window_ice',
            'aoa_ice',
            'stallwarning',
            'over_g',
            'over_vne',
            'over_vfe',
            'over_vle',
            'onground_any',
            'onground_all',
            'smoking',
            'lo_rotor_warning']),
          ('sim/flightmodel/forces/',
           ['fnrml_aero',
            'faxil_aero',
            'fside_aero',
            'fnrml_prop',
            'faxil_prop',
            'fside_prop',
            'g_nrml',
            'g_axil',
            'g_side',
            'faxil_gear',
            'fside_gear',
            'fnrml_gear',
            'vx_air_on_acf',
            'vy_air_on_acf',
            'vz_air_on_acf',
            'vx_acf_axis',
            'vy_acf_axis',
            'vz_acf_axis',
            'Q_rotor_rad',
            'R_rotor_rad',
            'vs',
            've',
            'lift_path_axis',
            'drag_path_axis',
            'side_path_axis']),
          ('sim/flightmodel/jetwash/',
           ['DVinc',
            'ringDVinc']),
          ('sim/flightmodel/misc/',
           ['ett_size',
            'jett_len',
            'g_total',
            'nosewheel_speed',
            'wing_tilt_ptch',
            'wing_tilt_roll',
            'ai_app_mode',
            'jato_left',
            'displace_rat',
            'h_ind',
            'h_ind2',
            'machno',
            'Qstatic',
            'turnrate_roll',
            'turnrate_roll2',
            'turnrate_noroll',
            'turnrate_noroll2',
            'slip',
            'time_jett_over',
            'rocket_mode',
            'rocket_timeout',
            'prop_ospeed_test_timeout',
            'blown_flap_engage_rat',
            'lift_fan_total_power',
            'stab_ptch_test',
            'stab_hdng_test',
            'cgz_ref_to_default',
            'i',
            'j',
            'Q_centroid_MULT',
            'C_m',
            'C_n',
            'cl_overall',
            'cd_overall',
            'l_o_d']),
          ('sim/flightmodel/ground/',
           ['surface_texture_type',
            'plugin_ground_center',
            'plugin_ground_slope_normal',
            'plugin_ground_terrain_velocity']),
          ('sim/flightmodel/movingparts/',
           ['gear1def',
            'gear2def',
            'gear3def',
            'gear4def',
            'gear5def',
            'wing_sweep1',
            'wing_sweep2',
            'wing_sweep3',
            'tvect']),
          ('sim/flightmodel/parts/',
           ['v_el',
            'alpha_el',
            'downwash_deg',
            'propwash_rat',
            'del_dir',
            'CL_grndeffect',
            'CD_grndeffect',
            'wash_grndeffect',
            'Q_centroid_loc',
            'Q_centroid_MULT',
            'stalled',
            'tire_locked',
            'tire_drag_dis',
            'tire_speed_term',
            'tire_speed_now',
            'tire_prop_rot',
            'tire_vrt_def_veh',
            'tire_vrt_frc_veh',
            'tire_steer_cmd',
            'tire_steer_act',
            'nrml_force',
            'axil_force',
            'force_XYZ',
            'flap_def',
            'flap2_def',
            'elev_cont_def',
            'elev_trim_def',
            'rudd_cont_def',
            'rudd2_cont_def',
            'foil_swe',
            'foil_dih',
            'foil_inc',
            'elem_inc']),
          ('sim/flightmodel/position/',
           ['local_x',
            'local_y',
            'local_z',
            'lat_ref',
            'lon_ref',
            'latitude',
            'longitude',
            'elevation',
            'theta',
            'phi',
            'psi',
            'magpsi',
            'local_vx',
            'local_vy',
            'local_vz',
            'local_ax',
            'local_ay',
            'local_az',
            'alpha',
            'beta',
            'vpath',
            'hpath',
            'groundspeed',
            'indicated_airspeed',
            'indicated_airspeed2',
            'true_airspeed',
            'magnetic_variation',
            'M',
            'N',
            'L',
            'P',
            'Q',
            'R',
            'P_dot',
            'Q_dot',
            'R_dot',
            'Prad',
            'Qrad',
            'Rrad',
            'q',
            'vh_ind',
            'vh_ind_fpm',
            'vh_ind_fpm2',
            'y_agl']),
          ('sim/flightmodel/weight/',
           ['m_fixed',
            'm_total',
            'm_fuel1',
            'm_fuel2',
            'm_fuel3',
            'm_jettison',
            'm_fuel_total']),
          ('sim/graphics/colors/',
           ['background_rgb',
            'menu_dark_rgb',
            'menu_hilite_rgb',
            'menu_lite_rgb',
            'menu_text_rgb',
            'menu_text_disabled_rgb',
            'subtitle_text_rgb',
            'tab_front_rgb',
            'tab_back_rgb',
            'caption_text_rgb',
            'list_text_rgb',
            'glass_text_rgb',
            'plane_path1_3d_rgb',
            'plane_path2_3d_rgb']),
          ('sim/graphics/misc/',
           ['show_panel_click_spots',
            'cockpit_light_level_r',
            'cockpit_light_level_g',
            'cockpit_light_level_b',
            'use_proportional_fonts',
            'scrolling_panel_size',
            'default_scroll_pos',
            'current_scroll_pos',
            'current_scroll_mode']),
          ('sim/graphics/scenery/',
           ['current_planet',
            'percent_lights_on',
            'sun_declination',
            'moon_declination',
            'sun_azimuth',
            'moon_azimuth',
            'earth_lat_loaded',
            'earth_lon_loaded',
            'mars_lat_loaded',
            'mars_lon_loaded',
            'airport_light_level']),
          ('sim/graphics/settings/',
           ['rendering_res',
            'autogen_level',
            'autogen_distance',
            'draw_aircrafts',
            'draw_obstacles',
            'draw_obstacles',
            'draw_textured_lites',
            'dim_gload',
            'draw_taxilines',
            'draw_forestfires',
            'draw_oilrigs',
            'draw_ships',
            'draw_vectors',
            'draw_cars',
            'transparent_panel',
            'draw_planes_on_ground']),
          ('sim/graphics/view/',
           ['view_type',
            'view_is_external',
            'view_x',
            'view_y',
            'view_z',
            'view_elevation_m_msl',
            'view_elevation_agl',
            'view_pitch',
            'view_roll',
            'view_heading',
            'cockpit_pitch',
            'cockpit_roll',
            'cockpit_heading',
            'view_zoom',
            'field_of_view_deg',
            'field_of_view_vertical_deg',
            'field_of_view_horizontal_deg',
            'field_of_view_vertical_ratio',
            'field_of_view_horizontal_ratio',
            'field_of_view_roll_deg',
            'elumens_ref_psi',
            'elumens_ref_the',
            'elumens_ref_phi',
            'number_elumens_projections',
            'elumens_tex_width',
            'elumens_tex_height',
            'window_width',
            'window_height',
            'visibility_effective_m',
            'visibility_terrain_m',
            'visibility_framerate_ratio',
            'visibility_math_level',
            'visibility_scale',
            'panel_total_pnl_l',
            'panel_total_pnl_b',
            'panel_total_pnl_r',
            'panel_total_pnl_t',
            'panel_visible_pnl_l',
            'panel_visible_pnl_b',
            'panel_visible_pnl_r',
            'panel_visible_pnl_t',
            'panel_total_win_l',
            'panel_total_win_b',
            'panel_total_win_r',
            'panel_total_win_t',
            'panel_visible_win_l',
            'panel_visible_win_b',
            'panel_visible_win_r',
            'panel_visible_win_t']),
          ('sim/joystick/',
           ['has_joystick',
            'mouse_is_joystick',
            'yolk_pitch_ratio',
            'yolk_roll_ratio',
            'yolk_heading_ratio',
            'artstab_pitch_ratio',
            'artstab_roll_ratio',
            'artstab_heading_ratio',
            'FC_hdng',
            'FC_ptch',
            'FC_roll',
            'joystick_pitch_nullzone',
            'joystick_roll_nullzone',
            'joystick_heading_nullzone',
            'joystick_pitch_sensitivity',
            'joystick_roll_sensitivity',
            'joystick_heading_sensitivity',
            'joystick_axis_assignments',
            'joystick_button_assignments',
            'joystick_axis_reverse',
            'joystick_axis_values',
            'joystick_axis_minimum',
            'joystick_axis_maximum',
            'joystick_button_values',
            'eq_ped_nobrk',
            'eq_ped_wibrk',
            'eq_cirrusII_fun',
            'eq_cirrusII_app',
            'eq_pfc_pedals',
            'eq_pfc_cirrus2',
            'eq_pfc_yoke',
            'eq_pfc_throt',
            'eq_pfc_avio',
            'eq_pfc_centercon',
            'eq_pfc_elec_trim',
            'eq_pfc_brake_tog',
            'eq_pfc_dual_cowl',
            'fire_key_is_down']),
          ('sim/joystick/pfc/',
           ['last_autopilot_button_input',
            'autopilot_lites']),
          ('sim/multiplayer/position/',
           ['plane1_x',
            'plane1_y',
            'plane1_z',
            'plane1_the',
            'plane1_phi',
            'plane1_psi',
            'plane1_gear_deploy',
            'plane1_flap_ratio',
            'plane1_flap_ratio2',
            'plane1_spoiler_ratio',
            'plane1_speedbrake_ratio',
            'plane1_slat_ratio',
            'plane1_wing_sweep',
            'plane1_throttle',
            'plane1_yolk_pitch',
            'plane1_yolk_roll',
            'plane1_yolk_yaw',
            'plane2_x',
            'plane2_y',
            'plane2_z',
            'plane2_the',
            'plane2_phi',
            'plane2_psi',
            'plane2_gear_deploy',
            'plane2_flap_ratio',
            'plane2_flap_ratio2',
            'plane2_spoiler_ratio',
            'plane2_speedbrake_ratio',
            'plane2_slat_ratio',
            'plane2_wing_sweep',
            'plane2_throttle',
            'plane2_yolk_pitch',
            'plane2_yolk_roll',
            'plane2_yolk_yaw',
            'plane3_x',
            'plane3_y',
            'plane3_z',
            'plane3_the',
            'plane3_phi',
            'plane3_psi',
            'plane3_gear_deploy',
            'plane3_flap_ratio',
            'plane3_flap_ratio2',
            'plane3_spoiler_ratio',
            'plane3_speedbrake_ratio',
            'plane3_slat_ratio',
            'plane3_wing_sweep',
            'plane3_throttle',
            'plane3_yolk_pitch',
            'plane3_yolk_roll',
            'plane3_yolk_yaw',
            'plane4_x',
            'plane4_y',
            'plane4_z',
            'plane4_the',
            'plane4_phi',
            'plane4_psi',
            'plane4_gear_deploy',
            'plane4_flap_ratio',
            'plane4_flap_ratio2',
            'plane4_spoiler_ratio',
            'plane4_speedbrake_ratio',
            'plane4_slat_ratio',
            'plane4_wing_sweep',
            'plane4_throttle',
            'plane4_yolk_pitch',
            'plane4_yolk_roll',
            'plane4_yolk_yaw',
            'plane5_x',
            'plane5_y',
            'plane5_z',
            'plane5_the',
            'plane5_phi',
            'plane5_psi',
            'plane5_gear_deploy',
            'plane5_flap_ratio',
            'plane5_flap_ratio2',
            'plane5_spoiler_ratio',
            'plane5_speedbrake_ratio',
            'plane5_slat_ratio',
            'plane5_wing_sweep',
            'plane5_throttle',
            'plane5_yolk_pitch',
            'plane5_yolk_roll',
            'plane5_yolk_yaw',
            'plane6_x',
            'plane6_y',
            'plane6_z',
            'plane6_the',
            'plane6_phi',
            'plane6_psi',
            'plane6_gear_deploy',
            'plane6_flap_ratio',
            'plane6_flap_ratio2',
            'plane6_spoiler_ratio',
            'plane6_speedbrake_ratio',
            'plane6_slat_ratio',
            'plane6_wing_sweep',
            'plane6_throttle',
            'plane6_yolk_pitch',
            'plane6_yolk_roll',
            'plane6_yolk_yaw',
            'plane7_x',
            'plane7_y',
            'plane7_z',
            'plane7_the',
            'plane7_phi',
            'plane7_psi',
            'plane7_gear_deploy',
            'plane7_flap_ratio',
            'plane7_flap_ratio2',
            'plane7_spoiler_ratio',
            'plane7_speedbrake_ratio',
            'plane7_slat_ratio',
            'plane7_wing_sweep',
            'plane7_throttle',
            'plane7_yolk_pitch',
            'plane7_yolk_roll',
            'plane7_yolk_yaw',
            'plane8_x',
            'plane8_y',
            'plane8_z',
            'plane8_the',
            'plane8_phi',
            'plane8_psi',
            'plane8_gear_deploy',
            'plane8_flap_ratio',
            'plane8_flap_ratio2',
            'plane8_spoiler_ratio',
            'plane8_speedbrake_ratio',
            'plane8_slat_ratio',
            'plane8_wing_sweep',
            'plane8_throttle',
            'plane8_yolk_pitch',
            'plane8_yolk_roll',
            'plane8_yolk_yaw',
            'plane9_x',
            'plane9_y',
            'plane9_z',
            'plane9_the',
            'plane9_phi',
            'plane9_psi',
            'plane9_gear_deploy',
            'plane9_flap_ratio',
            'plane9_flap_ratio2',
            'plane9_spoiler_ratio',
            'plane9_speedbrake_ratio',
            'plane9_slat_ratio',
            'plane9_wing_sweep',
            'plane9_throttle',
            'plane9_yolk_pitch',
            'plane9_yolk_roll',
            'plane9_yolk_yaw',
            'plane1_lat',
            'plane1_lon',
            'plane1_el',
            'plane1_v_x',
            'plane1_v_y',
            'plane1_v_z',
            'plane2_lat',
            'plane2_lon',
            'plane2_el',
            'plane2_v_x',
            'plane2_v_y',
            'plane2_v_z',
            'plane3_lat',
            'plane3_lon',
            'plane3_el',
            'plane3_v_x',
            'plane3_v_y',
            'plane3_v_z',
            'plane4_lat',
            'plane4_lon',
            'plane4_el',
            'plane4_v_x',
            'plane4_v_y',
            'plane4_v_z',
            'plane5_lat',
            'plane5_lon',
            'plane5_el',
            'plane5_v_x',
            'plane5_v_y',
            'plane5_v_z',
            'plane6_lat',
            'plane6_lon',
            'plane6_el',
            'plane6_v_x',
            'plane6_v_y',
            'plane6_v_z',
            'plane7_lat',
            'plane7_lon',
            'plane7_el',
            'plane7_v_x',
            'plane7_v_y',
            'plane7_v_z',
            'plane8_lat',
            'plane8_lon',
            'plane8_el',
            'plane8_v_x',
            'plane8_v_y',
            'plane8_v_z',
            'plane9_lat',
            'plane9_lon',
            'plane9_el',
            'plane9_v_x',
            'plane9_v_y',
            'plane9_v_z']),
          ('sim/network/dataout/',
           ['dump_next_cycle',
            'network_data_rate',
            'data_to_internet',
            'data_to_disk',
            'data_to_graph',
            'data_to_screen',
            'dump_parts_props',
            'dump_parts_wings',
            'dump_parts_vstabs']),
          ('sim/network/misc/',
           ['opentransport_inited',
            'connection_handshake',
            'network_time_sec']),
          ('sim/physics/',
           ['earth_mu',
            'mars_mu',
            'earth_radius_m',
            'mars_radius_m',
            'earth_temp_c',
            'mars_temp_c',
            'earth_pressure_p',
            'mars_pressure_p',
            'rho_sea_level',
            'mu_air',
            'g_sealevel',
            'pi',
            'double_pi',
            'half_pi',
            'R',
            'rho_water',
            'speed_light_m_sec']),
          ('sim/operation/failures/',
           ['hydraulic_pressure_ratio',
            'hydraulic_pressure_ratio2',
            'oil_power_thrust_ratio',
            'mean_time_between_failure_hrs',
            'ram_air_turbine_on', 
            'failures',
            'comp_fail_stat',
            'rel_vacuum',
            'rel_vacuum2',
            'rel_pitot',
            'rel_pitot2',
            'rel_static',
            'rel_static2',
            'rel_static1_err',
            'rel_static2_err',
            'rel_ss_asi',
            'rel_ss_ahz',
            'rel_ss_alt',
            'rel_ss_tsi',
            'rel_ss_dgy',
            'rel_ss_vvi',
            'rel_efis_1',
            'rel_efis_2',
            'rel_nav1',
            'rel_nav2',
            'rel_adf1',
            'rel_adf2',
            'rel_gps',
            'rel_dme',
            'rel_loc',
            'rel_gls',
            'rel_xpndr',
            'rel_instrument',
            'rel_fc_ail_L',
            'rel_fc_ail_R',
            'rel_fc_elv_U',
            'rel_fc_elv_D',
            'rel_fc_rud_L',
            'rel_fc_rud_R',
            'rel_trim_ail',
            'rel_trim_elv',
            'rel_trim_rud',
            'rel_fc_L_flp',
            'rel_fc_R_flp',
            'rel_L_flp_off',
            'rel_R_flp_off',
            'rel_lagear1',
            'rel_lagear2',
            'rel_lagear3',
            'rel_lagear4',
            'rel_lagear5',
            'rel_tire1',
            'rel_tire2',
            'rel_tire3',
            'rel_tire4',
            'rel_tire5',
            'rel_lbrakes',
            'rel_rbrakes',
            'rel_fc_slt',
            'rel_fc_thr',
            'rel_antice',
            'rel_clights',
            'rel_stbaug',
            'rel_otto',
            'rel_trotor',
            'rel_feather',
            'rel_throt_lo',
            'rel_throt_now',
            'rel_throt_hi',
            'rel_APU_press',
            'rel_depres_slow',
            'rel_depres_fast',
            'rel_hydsys',
            'rel_hydsys2',
            'rel_hydleak',
            'rel_hydleak2',
            'rel_hydoverp',
            'rel_hydoverp2',
            'rel_esys',
            'rel_esys2',
            'rel_invert0',
            'rel_invert1',
            'rel_invert1',
            'rel_invert2',
            'rel_invert3',
            'rel_invert4',
            'rel_invert5',
            'rel_invert6',
            'rel_invert7',
            'rel_engfai0',
            'rel_engfai1',
            'rel_engfai2',
            'rel_engfai3',
            'rel_engfai4',
            'rel_engfai5',
            'rel_engfai6',
            'rel_engfai7',
            'rel_engfir0',
            'rel_engfir1',
            'rel_engfir2',
            'rel_engfir3',
            'rel_engfir4',
            'rel_engfir5',
            'rel_engfir6',
            'rel_engfir7',
            'rel_pshaft0',
            'rel_pshaft1',
            'rel_pshaft2',
            'rel_pshaft3',
            'rel_pshaft4',
            'rel_pshaft5',
            'rel_pshaft6',
            'rel_pshaft7',
            'rel_seize_0',
            'rel_seize_1',
            'rel_seize_2',
            'rel_seize_3',
            'rel_seize_4',
            'rel_seize_5',
            'rel_seize_6',
            'rel_seize_7',
            'rel_revdep0',
            'rel_revdep1',
            'rel_revdep2',
            'rel_revdep3',
            'rel_revdep4',
            'rel_revdep5',
            'rel_revdep6',
            'rel_revdep7',
            'rel_engsep0',
            'rel_engsep1',
            'rel_engsep2',
            'rel_engsep3',
            'rel_engsep4',
            'rel_engsep5',
            'rel_engsep6',
            'rel_engsep7',
            'rel_oilpmp0',
            'rel_oilpmp1',
            'rel_oilpmp2',
            'rel_oilpmp3',
            'rel_oilpmp4',
            'rel_oilpmp5',
            'rel_oilpmp6',
            'rel_oilpmp7',
            'rel_fuepmp0',
            'rel_fuepmp1',
            'rel_fuepmp2',
            'rel_fuepmp3',
            'rel_fuepmp4',
            'rel_fuepmp5',
            'rel_fuepmp6',
            'rel_fuepmp7',
            'rel_lobatt0',
            'rel_lobatt1',
            'rel_lobatt2',
            'rel_lobatt3',
            'rel_lobatt4',
            'rel_lobatt5',
            'rel_lobatt6',
            'rel_lobatt7',
            'rel_genera0',
            'rel_genera1',
            'rel_genera2',
            'rel_genera3',
            'rel_genera4',
            'rel_genera5',
            'rel_genera6',
            'rel_genera7',
            'rel_fadec_0',
            'rel_fadec_1',
            'rel_fadec_2',
            'rel_fadec_3',
            'rel_fadec_4',
            'rel_fadec_5',
            'rel_fadec_6',
            'rel_fadec_7',
            'rel_runITT0',
            'rel_runITT1',
            'rel_runITT2',
            'rel_runITT3',
            'rel_runITT4',
            'rel_runITT5',
            'rel_runITT6',
            'rel_runITT7',
            'rel_comsta0',
            'rel_comsta1',
            'rel_comsta2',
            'rel_comsta3',
            'rel_comsta4',
            'rel_comsta5',
            'rel_comsta6',
            'rel_comsta7',
            'rel_fuelfl0',
            'rel_fuelfl1',
            'rel_fuelfl2',
            'rel_fuelfl3',
            'rel_fuelfl4',
            'rel_fuelfl5',
            'rel_fuelfl6',
            'rel_fuelfl7',
            'rel_ENGind0',
            'rel_ENGind1',
            'rel_ENGind2',
            'rel_ENGind3',
            'rel_ENGind4',
            'rel_ENGind5',
            'rel_ENGind6',
            'rel_ENGind7',
            'rel_PRPind0',
            'rel_PRPind1',
            'rel_PRPind2',
            'rel_PRPind3',
            'rel_PRPind4',
            'rel_PRPind5',
            'rel_PRPind6',
            'rel_PRPind7',
            'rel_N1_ind0',
            'rel_N1_ind1',
            'rel_N1_ind2',
            'rel_N1_ind3',
            'rel_N1_ind4',
            'rel_N1_ind5',
            'rel_N1_ind6',
            'rel_N1_ind7',
            'rel_N2_ind0',
            'rel_N2_ind1',
            'rel_N2_ind2',
            'rel_N2_ind3',
            'rel_N2_ind4',
            'rel_N2_ind5',
            'rel_N2_ind6',
            'rel_N2_ind7',
            'rel_TRQind0',
            'rel_TRQind1',
            'rel_TRQind2',
            'rel_TRQind3',
            'rel_TRQind4',
            'rel_TRQind5',
            'rel_TRQind6',
            'rel_TRQind7',
            'rel_FF_ind0',
            'rel_FF_ind1',
            'rel_FF_ind2',
            'rel_FF_ind3',
            'rel_FF_ind4',
            'rel_FF_ind5',
            'rel_FF_ind6',
            'rel_FF_ind7',
            'rel_EPRind0',
            'rel_EPRind1',
            'rel_EPRind2',
            'rel_EPRind3',
            'rel_EPRind4',
            'rel_EPRind5',
            'rel_EPRind6',
            'rel_EPRind7',
            'rel_ITTind0',
            'rel_ITTind1',
            'rel_ITTind2',
            'rel_ITTind3',
            'rel_ITTind4',
            'rel_ITTind5',
            'rel_ITTind6',
            'rel_ITTind7',
            'rel_wing1L',
            'rel_wing1R',
            'rel_wing2L',
            'rel_wing2R',
            'rel_wing3L',
            'rel_wing3R',
            'rel_wing4L',
            'rel_wing4R',
            'rel_hstbL',
            'rel_hstbR',
            'rel_vstb1',
            'rel_vstb2',
            'rel_mwing1',
            'rel_mwing2',
            'rel_mwing3',
            'rel_mwing4',
            'rel_mwing5',
            'rel_mwing6',
            'rel_mwing7',
            'rel_mwing8',
            'rel_pyl1a',
            'rel_pyl2a',
            'rel_pyl3a',
            'rel_pyl4a',
            'rel_pyl5a',
            'rel_pyl6a',
            'rel_pyl7a',
            'rel_pyl8a',
            'rel_pyl1b',
            'rel_pyl2b',
            'rel_pyl3b',
            'rel_pyl4b',
            'rel_pyl5b',
            'rel_pyl6b',
            'rel_pyl7b',
            'rel_pyl8b']),
          ('sim/operation/misc/',
           ['debug_network',
            'frame_rate_period',
            'time_ratio']),
          ('sim/operation/override/',
           ['override_joystick',
            'override_artstab',
            'override_flightcontrol',
            'override_gearbrake',
            'override_planepath',
            'override_navneedles',
            'override_adf',
            'override_dme',
            'override_gps',
            'override_flightdir',
            'override_flightdir_ptch',
            'override_flightdir_roll',
            'override_camera',
            'override_annunciators',
            'override_autopilot',
            'override_pfc_autopilot_lites',
            'override_joystick_heading',
            'override_joystick_pitch',
            'override_joystick_roll',
            'override_throttles',
            'override_groundplane',
            'disable_cockpit_object',
            'disable_twosided_fuselage']),
          ('sim/operation/prefs/',
           ['has_view_bitmap',
            'startup_on_ramp',
            'startup_running',
            'autopilot_grab_cur_speed',
            'autopilot_grab_cur_heading',
            'autopilot_grab_cur_vvi',
            'autopilot_grab_cur_altitude',
            'warn_overspeed',
            'warn_overgforce',
            'warn_overspeed_flaps',
            'warn_overspeed_gear',
            'reset_on_crash',
            'warn_nonobvious_stuff',
            'warn_framerate_low',
            'has_headset_on',
            'text_out',
            'replay_mode',
            'warn_bb',
            'aircraft_damping',
            'auto_coordinate_helos']),
          ('sim/operation/prefs/realweather/',
           ['check_real_weather_time_sec',
            'real_weather_max_vis_nm']),
          ('sim/operation/prefs/misc/',
           ['language']),
          ('sim/operation/sound/',
           ['has_sound',
            'has_speech_synth',
            'sound_on',
            'speech_on',
            'radio_chatter_on',
            'master_sound_volume']),
          ('sim/operation/windows/',
           ['system_window']),
          ('sim/time/',
           ['timer_is_running_sec',
            'total_running_time_sec',
            'total_flight_time_sec',
            'timer_elapsed_time_sec',
            'local_time_sec',
            'zulu_time_sec',
            'local_date_days',
            'use_system_time',
            'backwards',
            'paused',
            'hobbs_time']),
          ('sim/weapons/',
           ['weapon_count',
            'type',
            'free_flyer',
            'action_mode',
            'x_wpn_att',
            'y_wpn_att',
            'z_wpn_att',
            'cgY',
            'cgZ',
            'las_range',
            'conv_range',
            'bul_rounds_per_sec',
            'bul_rounds',
            'bul_muzzle_speed',
            'bul_area',
            'added_mass',
            'total_weapon_mass_max',
            'fuel_warhead_mass_max',
            'warhead_type',
            'mis_drag_co',
            'mis_drag_chute_S',
            'mis_cone_width',
            'mis_crat_per_deg_bore',
            'mis_crat_per_degpersec_bore',
            'mis_crat_per_degpersec',
            'gun_del_psi_deg_max',
            'gun_del_the_deg_max',
            'gun_del_psi_deg_now',
            'gun_del_the_deg_now',
            's_frn',
            's_sid',
            's_top',
            'X_body_aero',
            'Y_body_aero',
            'Z_body_aero',
            'Jxx_unitmass',
            'Jyy_unitmass',
            'Jzz_unitmass',
            'i',
            'j',
            'target_index',
            'targ_lat',
            'targ_lon',
            'targ_h',
            'del_psi',
            'del_the',
            'rudd_rat',
            'elev_rat',
            'V_msc',
            'AV_msc',
            'dist_targ',
            'dist_point',
            'time_point',
            'fx_axis',
            'fy_axis',
            'fz_axis',
            'vx',
            'vy',
            'vz',
            'x',
            'y',
            'z',
            'L',
            'M',
            'N',
            'Prad',
            'Qrad',
            'Rrad',
            'the',
            'psi',
            'phi',
            'the_con',
            'psi_con',
            'phi_con',
            'next_bull_time',
            'total_weapon_mass_now',
            'fuel_warhead_mass_now',
            'impact_time',
            'mis_thrust1',
            'mis_thrust2',
            'mis_thrust3',
            'mis_duration1',
            'mis_duration2',
            'mis_duration3',
            'q1',
            'q2',
            'q3',
            'q4']),
          ('sim/weather/',
           ['cloud_type',
            'cloud_base_msl_m',
            'cloud_tops_msl_m',
            'visibility_reported_m',
            'rain_percent',
            'thunderstorm_percent',
            'wind_turbulence_percent',
            'barometer_sealevel_inhg',
            'microburst_probability',
            'rate_change_percent',
            'has_real_weather_bool',
            'use_real_weather_bool',
            'sigma',
            'rho',
            'barometer_current_inhg',
            'gravity_mss',
            'speed_sound_ms',
            'wind_altitude_msl_m',
            'wind_direction_degt',
            'wind_speed_kt',
            'shear_direction_degt',
            'shear_speed_kt',
            'turbulence',
            'wave_amplitude',
            'wave_length',
            'wave_speed',
            'wave_dir',
            'temperature_sealevel_c',
            'dewpoi_sealevel_c',
            'temperature_ambient_c',
            'temperature_le_c',
            'thermal_percent',
            'thermal_rate_ms',
            'thermal_altitude_msl_m',
            'meteorite_density',
            'runway_friction',
            'wind_direction_degt',
            'wind_speed_kt'])
          ]

    #------------------------------------------------------------------------
    def __init__(self, child, bone=None):
        self.dataref=None	# None if null
        self.r=[]	# 0, 1 or 2 rotation vectors
        self.a=[]	# rotation angles (iff self.r)
        self.t=[]	# translation
        self.v=[]	# dataref value
        self.anim=None	# parent Anim

        if not child:
            return	# null
        
        object=child.parent
        if not object or object.getType()!='Armature':
            return

        if Blender.Get('version')<239:
            raise ExportError('Blender version 2.40 or later required for animation')

        if object.parent:
            raise ExportError("Armature \"%s\" has a parent; this is not supported. Use multiple bones within a single armature to represent complex movements." % object.name)
                
        if not bone:
            bonename=child.getParentBoneName()        
            if not bonename:
                raise ExportError("%s \"%s\" has an armature as a parent. It should have a bone as a parent." % (child.getType(), child.name))

            bones=object.getData().bones
            if isinstance(bones, list):	# 2.40a1/2
                for bone in object.getData().bones:
                    if bone.name==bonename:
                        break
            else:	# 2.40
                if bonename in bones.keys():
                    bone=bones[bonename]
            if not bone:
                raise ExportError("Missing animation data for bone \"%s\" in armature \"%s\"." % (bonename, object.name))	# wtf?

        name=bone.name
        l=name.find('.')
        if l!=-1:
            name=name[:l]
        l=name.find('[')
        if l!=-1:
            ref=name[:l]
        else:
            ref=name
        for (path, var) in Anim.refs:
            if ref in var:
                self.dataref=path+name
                break
        else:
            raise ExportError("Unrecognised dataref \"%s\" for bone in armature \"%s\"" % (name, child.name))

        if not (object.getAction() and
                object.getAction().getAllChannelIpos().has_key(bone.name)):
            print "Warn:\tYou haven't defined any keys for bone \"%s\" in armature \"%s\"." % (bone.name, object.name)
            if bone.parent:
                foo=Anim(child, bone.parent)
                self.dataref=foo.dataref
                self.r=foo.r
                self.a=foo.a
                self.t=foo.t
                self.v=foo.v
                self.anim=foo.anim
                return	#parent
            else:
                self.dataref=None
                return	#null
        ipo=object.getAction().getAllChannelIpos()[bone.name]

        if 0:	# debug
            for frame in [1,2]:            
                Blender.Set('curframe', frame)
                print "Frame\t%s" % frame
                print child
                print "local\t%s" % child.getMatrix('localspace').rotationPart().toEuler()
                print "\t%s" % child.getMatrix('localspace').translationPart()
                print "world\t%s" % child.getMatrix('worldspace').rotationPart().toEuler()
                print "\t%s" % child.getMatrix('worldspace').translationPart()
                print object
                print "local\t%s" % object.getMatrix('localspace').rotationPart().toEuler()
                print "\t%s" % object.getMatrix('localspace').translationPart()
                print "world\t%s" % object.getMatrix('worldspace').rotationPart().toEuler()
                print "\t%s" % object.getMatrix('worldspace').translationPart()
                print bone
                if 'getRestMatrix' in dir(bone):	# 2.40a1/2
                    print "bone\t%s" % bone.getRestMatrix('bonespace').rotationPart().toEuler()
                    print "\t%s" % bone.getRestMatrix('bonespace').translationPart()
                    print "world\t%s" % bone.getRestMatrix('worldspace').rotationPart().toEuler()
                    print "\t%s" % bone.getRestMatrix('worldspace').translationPart()
                else:	# 2.40
                    print "bone\t%s" % bone.matrix['BONESPACE'].rotationPart().toEuler()
                    #crashes print "\t%s" % bone.matrix['BONESPACE'].translationPart()
                    print "arm\t%s" % bone.matrix['ARMATURESPACE'].rotationPart().toEuler()
                    print "\t%s" % bone.matrix['ARMATURESPACE'].translationPart()
                #print "head\t%s" % bone.head
                #print "tail\t%s" % bone.tail
                #print "rot\t%s" % bone.quat.toEuler()
                #print "loc\t%s" % bone.loc
                print ipo
                q = Quaternion([ipo.getCurveCurval('QuatW'),
                                ipo.getCurveCurval('QuatX'),
                                ipo.getCurveCurval('QuatY'),
                                ipo.getCurveCurval('QuatZ')])
                print "ipo\t%s" % q.toEuler()
                print "\t%s %s" % (q.angle, q.axis)
                print "\t%s" % Vector([ipo.getCurveCurval('LocX'),
                                       ipo.getCurveCurval('LocY'),
                                       ipo.getCurveCurval('LocZ')])
            print

        if bone.parent:
            self.anim=Anim(child, bone.parent)
        else:
            self.anim=Anim(None)
    
        # Useful info in Blender 2.40a1&2:
        # child.getMatrix('localspace') - inconsistent - not useful
        # child.getMatrix('worldspace') - rot & trans post pose
        # armature.getMatrix('local/worldspace') - abs position pre pose
        # bone.getRestMatrix('bonespace') - broken
        # bone.getRestMatrix('worldspace') - rot & trans rel to arm pre pose
        # bone.head - broken
        # bone.tail - posn of tail rel to armature pre pose
        # ipo - bone position rel to rest posn post pose
        #
        # In X-Plane:
        # Transformations are relative to unrotated position and cumulative
        # Rotations are relative to each other (ie cumulative)
        
        for frame in [1,2]:            
            Blender.Set('curframe', frame)
            mm=Matrix(object.getMatrix('worldspace'))
            rm=mm.rotationPart()
            rm.resize4x4()
            if bone.parent:
                # Child offset should be relative to parent
                mm=rm

            if (ipo.getCurve('LocX') and
                ipo.getCurve('LocY') and
                ipo.getCurve('LocZ')):
                t = Vector([ipo.getCurveCurval('LocX'),
                            ipo.getCurveCurval('LocY'),
                            ipo.getCurveCurval('LocZ')])
            else:
                t = Vector(0,0,0)
            
            if 'getRestMatrix' in dir(bone):	# 2.40a1/2
                t=Vertex(t*bone.getRestMatrix('worldspace').rotationPart()+
                         bone.getRestMatrix('worldspace').translationPart(),mm)
            else:	# 2.40
                t=Vertex(t*bone.matrix['ARMATURESPACE'].rotationPart()+
                         bone.matrix['ARMATURESPACE'].translationPart(),mm)
            self.t.append(t)

            if (ipo.getCurve('QuatW') and
                ipo.getCurve('QuatX') and
                ipo.getCurve('QuatY') and
                ipo.getCurve('QuatZ')):
                q=Quaternion([ipo.getCurveCurval('QuatW'),
                              ipo.getCurveCurval('QuatX'),
                              ipo.getCurveCurval('QuatY'),
                              ipo.getCurveCurval('QuatZ')])
                if 'getRestMatrix' in dir(bone):	# 2.40a1/2
                    qr= Vertex(q.axis*bone.getRestMatrix('worldspace').rotationPart(), rm)	# In bone space
                else:	# 2.40
                    qr= Vertex(q.axis*bone.matrix['ARMATURESPACE'].rotationPart(), rm)	# In bone space
                a = round(q.angle, Vertex.ROUND)
                if a==0:
                    self.a.append(0)
                elif not self.r:
                    self.r.append(qr)
                    self.a.append(a)
                elif qr.equals(self.r[0]):
                    self.a.append(a)
                elif qr.equals(-self.r[0]):
                    self.a.append(-a)
                else:
                    # no common axis - add second axis
                    self.r.append(qr)
                    self.a.append(a)
            else:
                self.a.append(0)

        # dataref values v1 & v2
        for val in [1,2]:
            valstr="%s_v%d" % (ref, val)
            for prop in object.getAllProperties():
                if prop.name==valstr:
                    if prop.type=='INT':
                        self.v.append(prop.data)
                    elif prop.type=='FLOAT':
                        self.v.append(round(prop.data, Vertex.ROUND))
                    else:
                        raise ExportError("Unsupported data type for \"%s\" in armature \"%s\"" % (valstr, child.name))
                    break
            else:
                self.v.append(val-1)	# defaults = [0,1]


    #------------------------------------------------------------------------
    def __str__ (self):
        if self.dataref:
            return "%x %s r=%s a=%s t=%s v=%s p=(%s)" % (id(self), self.dataref, self.r, self.a, self.t, self.v, self.anim)
        else:
            return "None"

    #------------------------------------------------------------------------
    def equals (self, b):
        if self is b:
            return True
        if not self.dataref:	# null
            return not b.dataref
        if (self.dataref!=b.dataref or
            len(self.r)!=len(b.r) or
            not self.anim.equals(b.anim)):
            return False
        for i in range(len(self.r)):
            if not self.r[i].equals(b.r[i]):
                return False
        for i in [0,1]:
            if not ((not self.r or abs(self.a[i]-b.a[i])<=Vertex.LIMIT) and

                    self.t[i].equals(b.t[i]) and
                    self.v[i]==b.v[i]):
                return False
        return True

    #------------------------------------------------------------------------
    def ins(self):
        t=''
        anim=self
        while not anim.equals(Anim(None)):
            t=t+"\t"
            anim=anim.anim
        return t


#------------------------------------------------------------------------
if Blender.Window.EditMode():
    Blender.Draw.PupMenu('Please exit Edit Mode first.')
else:
    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l!=-1:
        baseFileName=baseFileName[:l]

    obj=OBJexport(baseFileName+'.obj')
    scene = Blender.Scene.getCurrent()
    try:
        obj.export(scene)
    except ExportError, e:
        Blender.Window.WaitCursor(0)
        Blender.Window.DrawProgressBar(0, 'ERROR')
        msg="ERROR:\t%s\n" % e.msg
        print msg
        Blender.Draw.PupMenu(msg)
        Blender.Window.DrawProgressBar(1, 'ERROR')
        if obj.file:
            obj.file.close()
