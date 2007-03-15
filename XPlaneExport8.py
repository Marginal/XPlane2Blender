#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane v8 Object (.obj)'
Blender: 240
Group: 'Export'
Tooltip: 'Export to X-Plane v8 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.26"
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
# X-Plane exporter for blender 2.40 or above
#
# Copyright (c) 2004,2005,2006 Jonathan Harris
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
# 2005-11-21 v2.13
#  - Don't emit redundant ATTR_[no_]shade attributes.
#  - Added optimisation to re-use points (but not indices) between animations.
#
# 2005-11-21 v2.14
#  - Speeded up point re-use optimisation.
#
# 2005-12-21 v2.15
#  - Handle armatures set in "Rest position" - requires 2.40.
#  - Tweaked progress bar.
#  - Add support for custom datarefs added by XPLMRegisterDataAccessor().
#
# 2006-01-05 v2.16
#  - Fix for relative and v8 texture paths.
#
# 2006-02-24 v2.18
#  - Import datarefs from DataRefs.txt. Add checking of type and arrayness.
#
# 2006-04-16 v2.20
#  - Translation fix for animations nested >=3 deep.
#  - Emit unit rotation vector even when Armature is scaled.
#  - Fix face direction when object negatively scaled.
#  - Fix face normal to be unit length when object is scaled.
#  - Default to ATTR_no_blend.
#
# 2006-04-22 v2.21
#  - Oops. ATTR_no_blend not such a good idea.
#
# 2006-07-19 v2.25
#  - Support for named lights, layer group, custom LOD ranges.
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
from XPlaneUtils import Vertex, UV, MatrixrotationOnly, getDatarefs
from XPlaneExport import *
#import time

datarefs={}


class VT:
    def __init__(self, v, n, uv):
        self.v=v
        self.n=n
        self.uv=uv

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f\t%s" % (self.v, self.n.x, self.n.y,
                                              self.n.z, self.uv)
            
    def equals (self, b, fudge=Vertex.LIMIT):
        return (self.v.equals(b.v, fudge) and
                self.n.equals(b.n, fudge) and
                self.uv.equals(b.uv))

class VLINE:
    def __init__(self, v, c):
        self.v=v
        self.c=c
    
    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f" % (self.v,
                                          round(self.c[0],2),
                                          round(self.c[1],2),
                                          round(self.c[2],2))
    def equals (self, b):
        return (self.v.equals(b.v) and self.c==b.c)

class VLIGHT:
    def __init__(self, v, c):
        self.v=v
        self.c=c

    def __str__ (self):
        return "%s\t%6.3f %6.3f %6.3f" % (self.v,
                                          round(self.c[0],2),
                                          round(self.c[1],2),
                                          round(self.c[2],2))

    def equals (self, b):
        return (self.v.equals(b.v) and self.c==b.c)

class NLIGHT:
    def __init__(self, v, n):
        self.v=v
        self.n=n	# (str) name or (list) custom

    def __str__ (self):
        return "%s\t%s%s" % (self.n, '\t'*(2-len(self.n)/8), self.v)

    def equals (self, b):
        return (self.v.equals(b.v) and self.c==b.c)


class Prim:
    # Flags in sort order
    HARD=1
    TWOSIDE=2
    NPOLY=4
    PANEL=8	# Should be 2nd last
    ALPHA=16	# Must be last
    
    BUCKET1=HARD|TWOSIDE|NPOLY
    # ANIM comes here
    BUCKET2=PANEL|ALPHA
    # LOD comes here

    def __init__ (self, layer, flags, anim):
        self.i=[]	# indices for lines & tris, VLIGHT/NLIGHT for lights
        self.anim=anim
        self.flags=flags
        self.layer=layer

    def match(self, layer, flags, anim):
        return (self.layer&layer and
                self.flags==flags and
                self.anim.equals(anim))


#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport8:

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
        self.group=None
        self.linewidth=0.101
        self.nprim=0		# Number of X-Plane primitives exported

        # attributes controlling export
        self.hard=False
        self.twoside=False
        self.npoly=True
        self.panel=False
        self.alpha=False	# implicit - doesn't appear in output file
        self.layer=0
        self.lod=None		# list of lod limits
        self.anim=Anim(None)

        # Global vertex lists
        self.vt=[]
        self.vline=[]
        self.anims=[Anim(None)]

        # primitive lists
        self.tris=[]
        self.lines=[]
        self.lights=[]
        self.nlights=[]		# named and custom lights

        self.animcands=[]	# indices into tris of candidates for reuse

    #------------------------------------------------------------------------
    def export(self, scene):
        theObjects = []
        theObjects = scene.getChildren()

        print 'Starting OBJ export to ' + self.filename
        if not checkFile(self.filename):
            return

        Blender.Window.WaitCursor(1)
        Window.DrawProgressBar(0, 'Examining textures')
        (self.texture,self.havepanel,self.layermask,
         self.lod)=getTexture(theObjects,self.layermask,self.iscockpit,False,8)
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
        #scene.update(1)
        #scene.makeCurrent()	# see Blender bug #4696
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
            Window.DrawProgressBar(float(nobj-o)*0.4/nobj,
                                   "Exporting %d%% ..." % ((nobj-o)*40/nobj))
            objType=object.getType()
            if objType == 'Mesh':
                if isLine(object, self.linewidth):
                    self.sortLine(object)
                else:
                    self.sortMesh(object)
            elif objType in ['Lamp', 'Armature']:
                pass	# these dealt with separately
            elif objType == 'Empty':
                for prop in object.getAllProperties():
                    if prop.type in ['INT', 'FLOAT'] and prop.name.startswith('group '):
                        self.group=(prop.name[6:].strip(), int(prop.data))
            else:
                print "Warn:\tIgnoring %s \"%s\"" % (objType.lower(),
                                                     object.name)

        # Lights
        for o in range (len(theObjects)-1,-1,-1):
            object=theObjects[o]
            if (object.getType()=='Lamp' and object.Layer&self.layermask):
                self.sortLamp(object)

        # Build ((1+Prim.ALPHA*2) *len(anims) *len(lseq)) indices
        indices=[]
        offsets=[]
        counts=[]
        progress=0.0
        for layer in lseq:
            for passhi in [0,Prim.PANEL,Prim.ALPHA,Prim.PANEL|Prim.ALPHA]:
                Window.DrawProgressBar(0.4+progress/(10*len(lseq)),
                                       "Exporting %d%% ..." % (40+progress*10/len(lseq)))
                progress+=1
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

        self.nprim=len(self.vt)+len(self.vline)+len(self.lights)+len(self.nlights)
        self.file.write("POINT_COUNTS\t%d %d %d %d\n\n" % (len(self.vt),
                                                           len(self.vline),
                                                           len(self.lights),
                                                           len(indices)))
        Window.DrawProgressBar(0.8, 'Exporting 80% ...')
        for vt in self.vt:
            self.file.write("VT\t%s\n" % vt)
        if self.vt:
            self.file.write("\n")

        for vline in self.vline:
            self.file.write("VLINE\t%s\n" % vline)
        if self.vline:
            self.file.write("\n")

        for light in self.lights:
            self.file.write("VLIGHT\t%s\n" % light.i)
        if self.lights:
            self.file.write("\n")

        Window.DrawProgressBar(0.9, 'Exporting 90% ...')
        n=len(indices)
        for i in range(0, n-9, 10):
            self.file.write("IDX10\t")
            for j in range(i, i+9):
                self.file.write("%d " % indices[j])
            self.file.write("%d\n" % indices[i+9])
        for j in range(n-(n%10), n):
            self.file.write("IDX\t%d\n" % indices[j])

        if self.group:
            self.file.write("\nATTR_layer_group\t%s\t%d\n" % (
                self.group[0], self.group[1]))
            
        # Geometry Commands
        n=0
        for layer in lseq:
            for passhi in [0,Prim.PANEL,Prim.ALPHA,Prim.PANEL|Prim.ALPHA]:
                for anim in self.anims:
                    # Lines
                    if counts[n]:
                        self.updateAttr(0, 0, 1, 0, 0, layer, anim)
                        self.file.write("%sLINES\t%d %d\n" %
                                        (anim.ins(), offsets[n], counts[n]))
                    n=n+1
                    
                    # Lights
                    i=0
                    while i<len(self.lights):
                        if self.lights[i].match(layer, passhi, anim):
                            self.updateAttr(0, 0, 1, passhi&Prim.PANEL, passhi&Prim.ALPHA, layer, anim)
                            for j in range(i+1, len(self.lights)):
                                if not self.lights[j].match(layer,passhi,anim):
                                    break
                            else:
                                j=len(self.lights)	# point past last match
                            self.file.write("%sLIGHTS\t%d %d\n" %
                                            (anim.ins(), i, j-i))
                            i=j
                        else:
                            i=i+1

                    # Named lights
                    for i in range(len(self.nlights)):
                        if self.nlights[i].match(layer,passhi,anim):
                            self.updateAttr(0, 0, 1, passhi&Prim.PANEL, passhi&Prim.ALPHA, layer, anim)
                            self.file.write("%sLIGHT_NAMED\t%s\n" %
                                            (anim.ins(), self.nlights[i].i))
                        
                    # Tris
                    for passno in range(passhi,passhi+Prim.BUCKET1+1):
                        if counts[n]:
                            self.updateAttr(passno&Prim.HARD,
                                            passno&Prim.TWOSIDE,
                                            passno&Prim.NPOLY,
                                            passno&Prim.PANEL,
                                            passno&Prim.ALPHA,
                                            layer, anim)
                            self.file.write("%sTRIS\t%d %d\n" %
                                            (anim.ins(), offsets[n],counts[n]))
                        n=n+1
    
        # Close animations in final layer
        while not self.anim.equals(Anim(None)):
            self.anim=self.anim.anim
            self.file.write("%sANIM_end\n" % self.anim.ins())

        self.file.write("\n# Built with Blender %4.2f. Exported with XPlane2Blender %s.\n" % (float(Blender.Get('version'))/100, __version__))


    #------------------------------------------------------------------------
    def sortLamp(self, object):

        (anim, mm)=self.makeAnim(object)
        light=Prim(object.Layer, Prim.ALPHA, anim)
        
        lamp=object.getData()
        name=object.name
        special=0
        
        if lamp.getType() != Lamp.Types.Lamp:
            print "Info:\tIgnoring Area, Spot, Sun or Hemi lamp \"%s\"" % name
            return
        
        if self.verbose:
            print "Info:\tExporting Light \"%s\"" % name

        if '.' in name: name=name[:name.index('.')]
        lname=name.lower().split()
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
        elif 'lamp' in lname:
            c[0]=lamp.col[0]
            c[1]=lamp.col[1]
            c[2]=lamp.col[2]
        else:	# named light
            light.i=NLIGHT(Vertex(0,0,0, mm), name)
            self.nlights.append(light)
            return

        light.i=VLIGHT(Vertex(0,0,0, mm), c)
        self.lights.append(light)


    #------------------------------------------------------------------------
    def sortLine(self, object):
        if self.verbose:
            print "Info:\tExporting Line \"%s\"" % object.name

        (anim, mm)=self.makeAnim(object)
        line=Prim(object.Layer, 0, anim)

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
        hasanim=not anim.equals(Anim(None))
        nm=MatrixrotationOnly(mm, object)
        # Vertex order, taking into account negative scaling
        if object.SizeX*object.SizeY*object.SizeZ<0:
            seq=[[],[],[],[0,1,2],[0,1,2,3]]
        else:
            seq=[[],[],[],[2,1,0],[3,2,1,0]]

        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
                
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(nmesh.faces))

        # Optimisation: Children of animations might be dupes. This test only
        # looks for exact duplicates, but this can reduce vertex count by ~10%.
        twosideerr=0
        harderr=0
        degenerr=0
        if hasanim:
            animcands=list(self.animcands)	# List of candidate tris
            trino=0
            fudge=Vertex.LIMIT*10		# Be more lenient
            for f in nmesh.faces:
                n=len(f.v)
                if not n in [3,4]:
                    pass
                elif not (f.mode & NMesh.FaceModes.INVISIBLE):
                    for i in seq[n]:
                        nmv=f.v[i]
                        vertex=Vertex(nmv[0], nmv[1], nmv[2], mm)
                        if not f.smooth:
                            norm=Vertex(f.no, nm)
                        else:
                            norm=Vertex(nmv.no, nm)
                        if f.mode & NMesh.FaceModes.TEX:
                            uv=UV(f.uv[i][0], f.uv[i][1])
                        else:	# File format requires something - using (0,0)
                            uv=UV(0,0)
                        vt=VT(vertex, norm, uv)

                        j=0
                        while j<len(animcands):
                            if not vt.equals(self.vt[self.tris[animcands[j]+trino].i[seq[n][i]]], fudge):
                                animcands.pop(j)	# no longer a candidate
                            else:
                                j=j+1

                    if not len(animcands):
                        break	# exhausted candidates
                    trino+=1
            else:
                # Success - re-use tris starting at self.vt[animcands[0]]
                trino=0
                for f in nmesh.faces:
                    n=len(f.v)
                    if not n in [3,4]:
                        degenerr+=1
                    elif not (f.mode & NMesh.FaceModes.INVISIBLE):
                        face=Prim(object.Layer, 0, anim)
           
                        if f.mode & NMesh.FaceModes.TEX:
                            if len(f.uv)!=n:
                                raise ExportError("Missing UV in mesh \"%s\"" % object.name)
                            if f.transp == NMesh.FaceTranspModes.ALPHA:
                                face.flags|=Prim.ALPHA
        
                        if f.mode & NMesh.FaceModes.TWOSIDE:
                            face.flags|=Prim.TWOSIDE
                            twosideerr=twosideerr+1
        
                        if not f.mode&NMesh.FaceModes.TILES or self.iscockpit:
                            face.flags|=Prim.NPOLY
                            
                        if f.image and 'panel.' in f.image.name.lower():
                            face.flags|=Prim.PANEL
                        elif not (f.mode&NMesh.FaceModes.DYNAMIC or self.iscockpit):
                            face.flags|=Prim.HARD
                            harderr=harderr+1

                        for i in range(n):
                            face.i.append(self.tris[animcands[0]+trino].i[i])
                            
                        self.tris.append(face)
                        trino+=1
                
                if degenerr and self.verbose:
                    print "Info:\tIgnoring %s degenerate face(s) in mesh \"%s\"" % (degenerr, object.name)
                if harderr:
                    print "Info:\tFound %s hard face(s) in mesh \"%s\"" % (harderr, object.name)
                if twosideerr:
                    print "Info:\tFound %s two-sided face(s) in mesh \"%s\"" % (twosideerr, object.name)

                return

        # Either no animation, or no matching animation
        twosideerr=0
        harderr=0
        degenerr=0
        starttri=len(self.tris)
        # Optimisation: Build list of faces and vertices
        vti = [[] for i in range(len(nmesh.verts))]	# indices into vt

        for f in nmesh.faces:
            n=len(f.v)
            if not n in [3,4]:
                degenerr+=1
            elif not (f.mode & NMesh.FaceModes.INVISIBLE):
                face=Prim(object.Layer, 0, anim)
   
                if f.mode & NMesh.FaceModes.TEX:
                    if len(f.uv)!=n:
                        raise ExportError("Missing UV in mesh \"%s\"" % object.name)
                    if f.transp == NMesh.FaceTranspModes.ALPHA:
                        face.flags|=Prim.ALPHA

                if f.mode & NMesh.FaceModes.TWOSIDE:
                    face.flags|=Prim.TWOSIDE
                    twosideerr=twosideerr+1

                if not f.mode&NMesh.FaceModes.TILES or self.iscockpit:
                    face.flags|=Prim.NPOLY
                    
                if f.image and 'panel.' in f.image.name.lower():
                    face.flags|=Prim.PANEL
                elif not (f.mode&NMesh.FaceModes.DYNAMIC or self.iscockpit):
                    face.flags|=Prim.HARD
                    harderr=harderr+1

                for i in seq[n]:
                    nmv=f.v[i]
                    vertex=Vertex(nmv[0], nmv[1], nmv[2], mm)
                    if not f.smooth:
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
                    for j in vti[nmv.index]:		# Search this vertex
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

        if hasanim:
            # Save tris for matching next
            self.animcands.append(starttri)

        if degenerr and self.verbose:
            print "Info:\tIgnoring %s degenerate face(s) in mesh \"%s\"" % (
                degenerr, object.name)
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

        # Need to unset resting position of parent armature (if any)
        resting=False
        object=child.parent
        if (object and object.getType()=='Armature' and
            object.getData().restPosition):
            resting=True
            object.getData().restPosition=False

        # Add parent anims first
        al=[]
        a=anim
        while not a.equals(Anim(None)):
            al.insert(0, a)
            a=a.anim

        Blender.Set('curframe', 1)
        #scene=Blender.Scene.getCurrent()
        #scene.update(1)
        #scene.makeCurrent()	# see Blender bug #4696

        #mm=Matrix(child.getMatrix('localspace')) doesn't work in 2.40alpha
        mm=child.getMatrix('worldspace')
        
        for a in al:
            # Hack!
            # We need the position of the child in bone space - ie
            # rest position relative to bone root.
            # child.getMatrix('localspace') doesn't return this in 2.40.
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

        # Restore rest state
        if resting:
            object.getData().restPosition=True

        return (anim, mm)


    #------------------------------------------------------------------------
    def updateAttr(self, hard, twoside, npoly, panel, alpha, layer,anim):

        if layer!=self.layer:
            # Reset all attributes
            while not self.anim.equals(Anim(None)):
                self.anim=self.anim.anim
                self.file.write("%sANIM_end\n" % self.anim.ins())
            self.hard=False
            self.twoside=False
            self.npoly=True
            self.panel=False
            self.alpha=False
                
            if self.layermask==1:
                self.file.write("\n")
            else:
                self.file.write("\nATTR_LOD\t%d %d\n" % (
                    self.lod[layer/2], self.lod[layer/2+1]))
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
                    if self.anim.t[0].equals(self.anim.t[1]):
                        # save a potential accessor callback
                        self.file.write("%sANIM_trans\t%s\t%s\t%s %s\t%s\n" % (
                            self.anim.ins(), self.anim.t[0], self.anim.t[1],
                            0, 0, 'no_ref'))
                    else:
                        self.file.write("%sANIM_trans\t%s\t%s\t%s %s\t%s\n" % (
                            self.anim.ins(), self.anim.t[0], self.anim.t[1],
                            self.anim.v[0], self.anim.v[1], self.anim.dataref))
                if len(self.anim.r)==1:
                    self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[0],
                        self.anim.a[0], self.anim.a[1],
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                elif len(self.anim.r)==2:
                    self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[0],
                        self.anim.a[0], 0,
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                    self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n" % (
                        self.anim.ins(), self.anim.r[1],
                        0, self.anim.a[1],
                        self.anim.v[0], self.anim.v[1], self.anim.dataref))
                        

        # For readability, write turn-offs before turn-ons

        if self.hard and not hard:
            self.file.write("%sATTR_no_hard\n" % self.anim.ins())

        if self.twoside and not twoside:
            self.file.write("%sATTR_cull\n" % self.anim.ins())

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

        if npoly and not self.npoly:
            self.file.write("%sATTR_poly_os\t0\n" % self.anim.ins())

        if panel and not self.panel:
            self.file.write("%sATTR_cockpit\n" % self.anim.ins())

        # alpha is implicit - doesn't appear in output file
        if alpha and not self.alpha:
            self.file.write("%s####_alpha\n" % self.anim.ins())

        self.hard=hard
        self.twoside=twoside
        self.npoly=npoly
        self.panel=panel
        self.alpha=alpha


#------------------------------------------------------------------------
class Anim:
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

        if Blender.Get('version')<240:
            raise ExportError('Blender version 2.40 or later required for animation')

        if object.parent:
            raise ExportError('Armature "%s" has a parent; this is not supported. Use multiple bones within a single armature to represent complex animations.' % object.name)
                
        if not bone:
            bonename=child.getParentBoneName()        
            if not bonename:
                raise ExportError('%s "%s" has an armature as a parent. It should have a bone as a parent.' % (child.getType(), child.name))

            bones=object.getData().bones
            if bonename in bones.keys():
                bone=bones[bonename]
            else:
                raise ExportError('Missing animation data for bone "%s" in armature "%s".' % (bonename, object.name))	# wtf?

        name=bone.name
        l=name.find('.')
        if l!=-1:
            name=name[:l]
        name=name.strip()
        l=name.find('[')
        if l!=-1:
            ref=name[:l]
            idx=name[l+1:-1]
            if name[-1]!=']' or not idx or not idx.isdigit():
                raise ExportError('Malformed dataref index "%s" in bone "%s" in armature "%s"' % (name[l:], name, child.name))
            idx=int(idx)
        else:
            ref=name
            idx=None

        for prop in object.getAllProperties():
            if prop.name==ref:
                # custom dataref
                if prop.type=='STRING':
                    if prop.data[-1]!='/':
                        self.dataref=prop.data+'/'+name
                    else:
                        self.dataref=prop.data+name
                    break
                else:
                    raise ExportError('Unsupported data type for path of custom dataref "%s" in armature "%s".' % (ref, child.name))
        else:
            if ref in datarefs:
                (path, n)=datarefs[ref]
                if n==0:
                    raise ExportError('Dataref %s (used in armature "%s") can\'t be used for animation.' % (path+ref, child.name))
                elif n==1 and idx!=None:
                    raise ExportError('Dataref %s is not an array. Rename the bone in armature "%s" to "%s".' % (path+ref, child.name, ref))
                elif n!=1 and idx==None:
                    raise ExportError('Dataref %s is an array. Rename the bone in armature "%s" to "%s[0]" to use the first value, etc.' % (path+ref, child.name, ref))                
                self.dataref=path+name
            else:
                raise ExportError('Unrecognised dataref "%s" for bone in armature "%s".' % (name, child.name))
            
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
                        raise ExportError('Unsupported data type for "%s" in armature "%s".' % (valstr, child.name))
                    break
            else:
                self.v.append(val-1)	# defaults = [0,1]

        if not (object.getAction() and
                object.getAction().getAllChannelIpos().has_key(bone.name)):
            print 'Warn:\tYou haven\'t created any animation keys for bone "%s" in armature "%s". Skipping this animation.' % (bone.name, object.name)
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

        scene=Blender.Scene.getCurrent()
        if 0:	# debug
            for frame in [1,2]:            
                Blender.Set('curframe', frame)
                #scene.update(1)
                #scene.makeCurrent()	# see Blender bug #4696
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
                print "bone\t%s" % bone.matrix['BONESPACE'].rotationPart().toEuler()
                #crashes print "\t%s" % bone.matrix['BONESPACE'].translationPart()
                print "arm\t%s" % bone.matrix['ARMATURESPACE'].rotationPart().toEuler()
                print "\t%s" % bone.matrix['ARMATURESPACE'].translationPart()
                print "head\t%s" % bone.head
                print "tail\t%s" % bone.tail
                print "roll\t%s" % bone.roll
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
    
        # Useful info in Blender 2.40:
        # child.getMatrix('localspace') - rot & trans rel to arm pre pose
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
            #scene.update(1)
            #scene.makeCurrent()	# see Blender bug #4696
            mm=Matrix(object.getMatrix('worldspace'))
            # mm.rotationPart() scaled to be unit size for rotation axis
            rm=MatrixrotationOnly(mm, object)
            
            if (ipo.getCurve('LocX') and
                ipo.getCurve('LocY') and
                ipo.getCurve('LocZ')):
                t = Vector([ipo.getCurveCurval('LocX'),
                            ipo.getCurveCurval('LocY'),
                            ipo.getCurveCurval('LocZ')])
            else:
                t = Vector(0,0,0)

            t=Vertex(t*bone.matrix['ARMATURESPACE'].rotationPart()+
                     bone.matrix['ARMATURESPACE'].translationPart(),mm)
            # Child offset should be relative to parent
            anim=self.anim
            while not anim.equals(Anim(None)):
                t=t-anim.t[frame-1]
                anim=anim.anim
            self.t.append(t)

            if (ipo.getCurve('QuatW') and
                ipo.getCurve('QuatX') and
                ipo.getCurve('QuatY') and
                ipo.getCurve('QuatZ')):
                q=Quaternion([ipo.getCurveCurval('QuatW'),
                              ipo.getCurveCurval('QuatX'),
                              ipo.getCurveCurval('QuatY'),
                              ipo.getCurveCurval('QuatZ')])
                # In bone space
                qr=Vertex(q.axis*bone.matrix['ARMATURESPACE'].rotationPart(),
                          rm)
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
    obj=None
    try:
        datarefs=getDatarefs()
        obj=OBJexport8(baseFileName+'.obj')
        scene = Blender.Scene.getCurrent()
        obj.export(scene)
    except ExportError, e:
        Blender.Window.WaitCursor(0)
        Blender.Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s\n" % e.msg
        Blender.Draw.PupMenu("ERROR: %s" % e.msg)
        Blender.Window.DrawProgressBar(1, 'ERROR')
        if obj and obj.file:
            obj.file.close()
    except IOError, e:
        Blender.Window.WaitCursor(0)
        Blender.Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s\n" % e.strerror
        Blender.Draw.PupMenu("ERROR: %s" % e.strerror)
        Blender.Window.DrawProgressBar(1, 'ERROR')
        if obj and obj.file:
            obj.file.close()
