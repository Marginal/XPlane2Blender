#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane v8 Object (.obj)'
Blender: 243
Group: 'Export'
Tooltip: 'Export to X-Plane v8 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "2.46"
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
# X-Plane exporter for blender 2.43 or above
#
# Copyright (c) 2004-2007 Jonathan Harris
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
# 2006-07-19 v2.26
#  - Support for named lights, layer group, custom LOD ranges.
#
# 2006-07-30 v2.28
#  - Light names taken from "name" property, if present.
#  - Support for ANIM_show/hide.
#  - Support for ATTR_hard <surface>.
#  - Support for materials.
#  - Add sorting by group name.
#
# 2006-08-17 v2.30
#  - Speed up export by successively filtering triangle list.
#  - Support for slung_load_weight.
#
# 2006-10-03 v2.31
#  - Fix for nested animation translations.
#
# 2006-10-03 v2.32
#  - Fix for animations with duplicate show/hide values.
#
# 2006-12-04 v2.34
#  - Fix for weird sim/weather datarefs.
#  - ANIM_show/hide commands output in order found.
#
# 2007-02-26 v2.35
#  - Select problematic objects on error.
#  - Check for ambiguous dataref leaf names.
#  - Check that dataref indices don't exceed length of array.
#
# 2007-05-09 v2.37
#  - Allow a bone to be a child of a bone in another armature.
#  - Support for smoke_black and smoke_white.
#
# 2007-06-14 v2.39
#  - Use Mesh instead of NMesh for speed.
#  - Support for mesh modifiers.
#  - Info and warnings reported in popup menu - selects objects referred to.
#
# 2007-06-19 v2.40
#  - Fix for models with groups and multiple LODs.
#
# 2007-09-06 v2.41
#  - Tweaked ordering: Lines and Lights after tris. npoly has highest priority.
#
# 2007-09-19 v2.43
#  - Fix for lights in animated models.
#
# 2007-10-02 v2.44
#  - Only correctly named files are treated as cockpit objects.
#
# 2007-11-30 v2.46
#  - Support for custom lights.
#  - Fix for bones connected to parent with "Con" button.
#


#
# X-Plane renders polygons in scenery files mostly in the order that it finds
# them - it detects use of alpha and deletes wholly transparent polys, but
# doesn't sort by Z-buffer order.
#
# So we have to sort on export to ensure alpha comes after non-alpha. We also
# sort to minimise attribute state changes, in rough order of expense:
#  - Hard - should be first. Renderer merges hard polys with similar non-hard.
#  - TWOSIDE
#  - Materials
#  - Animations
#  - PANEL - most expensive, put as late as we can
#  - ALPHA - must be last for correctness. Renderer will merge with previous.
#  - NPOLY - negative so polygon offsets come first. Assumed to be on ground
#            so no ordering issues, so can be higher priority than ALPHA.
#  - Lines and lights
#  - Group
#  - Layer
#

import sys
import Blender
from Blender import Armature, Mesh, Lamp, Image, Draw, Window
from Blender.Mathutils import Matrix, RotationMatrix, TranslationMatrix, MatMultVec, Vector, Quaternion, Euler
from XPlaneUtils import Vertex, UV, MatrixrotationOnly, getDatarefs
from XPlaneExport import *
#import time

datarefs={}

# Default X-Plane (not Blender) material (ambient & specular do jack)
DEFMAT=((1,1,1), (0,0,0), 0)	# diffuse, emission, shiny

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
        self.n=n	# name

    def __str__ (self):
        return "LIGHT_NAMED\t%s\t%s%s" % (self.n, '\t'*(2-len(self.n)/8), self.v)

    def equals (self, b):
        return (isinstance(b,NLIGHT) and self.v.equals(b.v) and self.n==b.n)

class CLIGHT:
    def __init__(self, v, rgba, s, uv1, uv2, d):
        self.v=v
        self.rgba=rgba
        self.s=s
        self.uv1=uv1
        self.uv2=uv2
        self.d=d	# dataref

    def __str__ (self):
        return "LIGHT_CUSTOM\t%s\t%6.3f %6.3f %6.3f %6.3f %9.4f\t%s %s\t%s" % (self.v, self.rgba[0], self.rgba[1], self.rgba[2], self.rgba[3], self.s, self.uv1, self.uv2, self.d)

    def equals (self, b):
        return (isinstance(b,CLIGHT) and self.v.equals(b.v) and self.n==b.n)

class SMOKE:
    def __init__(self, v, n, p):
        self.v=v
        self.n=n	# smoke_black or smoke_white
        self.p=p	# puff

    def __str__ (self):
        return "%s\t%s\t%4.2f" % (self.n, self.v, self.p)

    def equals (self, b):
        return (isinstance(b,SMOKE) and self.v.equals(b.v) and self.n==b.n and self.p==b.p)


class Prim:
    # Flags in sort order
    TWOSIDE=1
    PANEL=2	# Should be 2nd last
    ALPHA=4	# Must be last
    NPOLY=8

    SURFACES=[False, True, 'water', 'concrete', 'asphalt', 'grass', 'dirt', 'gravel', 'lakebed', 'snow', 'shoulder', 'blastpad']	# default is first

    # surface comes here
    BUCKET1=TWOSIDE
    # material comes here
    # anim comes here
    BUCKET2=PANEL|ALPHA|NPOLY
    # lines and lights drawn here
    LINES  =BUCKET2
    LIGHTS =BUCKET2
    # group comes here
    # layer comes here

    def __init__ (self, layer, group, flags, surface, mat, anim):
        self.i=[]	# indices for lines & tris, VLIGHT/NLIGHT for lights
        self.anim=anim
        self.flags=flags	# bitmask
        self.surface=surface	# tris: one of Prim.SURFACES
        self.mat=mat		# tris: (diffuse, emission, shiny)
        self.group=group
        self.layer=layer

    def match(self, layer, group, flags, surface, mat, anim):
        return (self.layer&layer and
                self.group==group and
                self.flags==flags and
                self.surface==surface and
                self.mat==mat and
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
        self.iscockpit=(filename.lower().endswith("_cockpit.obj") or
                        filename.lower().endswith("_cockpit_inn.obj") or
                        filename.lower().endswith("_cockpit_out.obj"))
        self.layermask=1
        self.texture=None
        self.drawgroup=None
        self.slung=0
        self.linewidth=0.101
        self.nprim=0		# Number of X-Plane primitives exported
        self.log=[]

        # attributes controlling export
        self.surface=False
        self.mat=DEFMAT
        self.twoside=False
        self.npoly=True
        self.panel=False
        self.alpha=False	# implicit - doesn't appear in output file
        self.layer=0
        self.group=None
        self.lod=None		# list of lod limits
        self.anim=Anim(self, None)

        # Global vertex lists
        self.vt=[]
        self.vline=[]
        self.anims=[Anim(self, None)]
        self.mats=[DEFMAT]	# list of (diffuse, emission, shiny)
        if Blender.Get('version')>=242:	# new in 2.42
            self.groups=Blender.Group.Get()
            self.groups.sort(lambda x,y: cmp(x.name.lower(), y.name.lower()))
        else:
            self.groups=[]

        # primitive lists
        self.tris=[]
        self.lines=[]
        self.lights=[]
        self.vlights=[]
        self.nlights=[]		# named and custom lights

        self.animcands=[]	# indices into tris of candidates for reuse

    #------------------------------------------------------------------------
    def export(self, scene):
        theObjects = scene.objects

        print 'Starting OBJ export to ' + self.filename
        if not checkFile(self.filename):
            return

        Window.WaitCursor(1)
        Window.DrawProgressBar(0, 'Examining textures')
        self.texture=getTexture(self,theObjects,False,8)
        
        #clock=time.clock()	# Processor time
        frame=Blender.Get('curframe')

        self.file = open(self.filename, 'w')
        self.writeHeader ()
        self.writeObjects (theObjects)
        checkLayers (self, theObjects)
        
        Blender.Set('curframe', frame)
        #scene.update(1)
        #scene.makeCurrent()	# see Blender bug #4696
        Window.DrawProgressBar(1, 'Finished')
        Window.WaitCursor(0)
        #print "%s CPU time" % (time.clock()-clock)
        print "Finished - exported %s primitives\n" % self.nprim
        if self.log:
            r=Draw.PupMenu(("Exported %s primitives%%t|" % self.nprim)+'|'.join([a[0] for a in self.log]))
            if r>0: raise ExportError(None, self.log[r-1][1])
        else:
            Draw.PupMenu("Exported %s primitives%%t|OK" % self.nprim)

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

        # Speed optimisation
        if self.iscockpit:
            surfaces=[False]
        else:
            surfaces=Prim.SURFACES
            
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
                elif isLight(object):
                    self.sortLamp(object)                    
                else:
                    self.sortMesh(object)
            #elif objType in ['Curve','Surf']:
            #    self.sortMesh(object)
            elif objType=='Lamp':
                self.sortLamp(object)
            elif objType=='Armature':
                pass	# dealt with separately
            elif objType == 'Empty':
                for prop in object.getAllProperties():
                    if prop.type in ['INT', 'FLOAT'] and prop.name.strip().startswith('group_'):
                        self.drawgroup=(prop.name.strip()[6:], int(prop.data))
                        if not self.drawgroup[0] in ['terrain', 'beaches', 'shoulders', 'taxiways', 'runways', 'markings', 'airports', 'roads', 'objects', 'light_objects', 'cars']:
                            raise ExportError('Invalid drawing group "%s" in "%s"' % (self.drawgroup[0], object.name), [object])
                    elif prop.type in ['INT', 'FLOAT', 'STRING'] and prop.name.strip()=='slung_load_weight':
                        self.slung=prop.data
            #elif objType not in ['Camera','Lattice']:
            #    print 'Warn:\tIgnoring %s "%s"' % (objType.lower(),object.name)
            #    self.log.append(('Ignoring %s "%s"' % (objType.lower(), object.name),[object]))

        # Build indices
        indices=[]
        offsets=[]
        counts=[]
        progress=0.0
        for layer in lseq:
            # Hack!: Can't have hard tris outside layer 1
            if layer==2:
                for tri in self.tris: tri.surface=False
            tris1=[tri for tri in self.tris if tri.layer&layer]
            for group in [None]+self.groups:
                tris2=[tri for tri in tris1 if tri.group==group]
                for passhi in range(0, Prim.BUCKET2+1, Prim.BUCKET1+1):
                    Window.DrawProgressBar(0.4+progress/(10*len(lseq)),
                                           "Exporting %d%% ..." % (40+progress*10/len(lseq)))
                    progress+=1
                    for anim in self.anims:
                        tris3=[tri for tri in tris2 if tri.anim.equals(anim)]

                        # Tris
                        for mat in self.mats:
                            tris4=[tri for tri in tris3 if tri.mat==mat]
                            for passno in range(passhi,passhi+Prim.BUCKET1+1):
                                tris5=[tri for tri in tris4 if tri.flags==passno]
                                for surface in surfaces:
                                    index=[]
                                    offsets.append(len(indices))
                                    for tri in tris5:
                                        if tri.surface==surface:
                                            index.append(tri.i[0])
                                            index.append(tri.i[1])
                                            index.append(tri.i[2])
                                            if len(tri.i)==4:	# quad
                                                index.append(tri.i[0])
                                                index.append(tri.i[2])
                                                index.append(tri.i[3])
                                    counts.append(len(index))
                                    indices.extend(index)

                        # Lines
                        index=[]
                        offsets.append(len(indices))
                        for line in self.lines:
                            if line.match(layer, group, passhi, False, DEFMAT, anim):
                                index.append(line.i[0])
                                index.append(line.i[1])
                        counts.append(len(index))
                        indices.extend(index)

                        # Lights
                        offsets.append(len(self.vlights))
                        for light in self.lights:
                            if light.match(layer, group, passhi, False, DEFMAT, anim):
                                # ensure 1 LIGHTS statement
                                self.vlights.append(light)
                        counts.append(len(self.vlights)-offsets[-1])

        self.nprim=len(self.vt)+len(self.vline)+len(self.vlights)+len(self.nlights)
        self.file.write("POINT_COUNTS\t%d %d %d %d\n\n" % (len(self.vt),
                                                           len(self.vline),
                                                           len(self.vlights),
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

        for light in self.vlights:
            self.file.write("VLIGHT\t%s\n" % light.i)
        if self.vlights:
            self.file.write("\n")

        Window.DrawProgressBar(0.9, 'Exporting 90% ...')
        n=len(indices)
        for i in range(0, n-9, 10):
            self.file.write("IDX10\t"+' '.join([str(j) for j in indices[i:i+10]])+"\n")
        for i in range(n-(n%10), n):
            self.file.write("IDX\t%d\n" % indices[i])

        if self.slung:
            self.file.write("\nslung_load_weight\t%s\n" % self.slung)
        if self.drawgroup:
            self.file.write("\nATTR_layer_group\t%s\t%d\n" % (
                self.drawgroup[0], self.drawgroup[1]))

        # Geometry Commands
        # Order of loops must be *exactly* the same as above
        n=0
        for layer in lseq:
            for group in [None]+self.groups:
                for passhi in range(0, Prim.BUCKET2+1, Prim.BUCKET1+1):
                    for anim in self.anims:
                        # Tris
                        for mat in self.mats:
                            for passno in range(passhi,passhi+Prim.BUCKET1+1):
                                for surface in surfaces:
                                    if counts[n]:
                                        self.updateAttr(layer, group, anim,
                                                        surface, mat,
                                                        passno&Prim.TWOSIDE,
                                                        passno&Prim.NPOLY,
                                                        passno&Prim.PANEL,
                                                        passno&Prim.ALPHA)
                                        self.file.write("%sTRIS\t%d %d\n" %
                                                        (anim.ins(), offsets[n],counts[n]))
                                    n=n+1
                        # Lines
                        if counts[n]:
                            self.updateAttr(layer, group, anim)
                            self.file.write("%sLINES\t%d %d\n" %
                                            (anim.ins(),offsets[n],counts[n]))
                        n=n+1
                        
                        # Lights
                        if counts[n]:
                            self.updateAttr(layer, group, anim)
                            self.file.write("%sLIGHTS\t%d %d\n" %
                                            (anim.ins(),offsets[n],counts[n]))
                        n=n+1
    
                        # Named and custom lights
                        for i in range(len(self.nlights)):
                            if self.nlights[i].match(layer, group, passhi, False, DEFMAT, anim):
                                self.updateAttr(layer, group, anim)
                                self.file.write("%s%s\n" %
                                                (anim.ins(), self.nlights[i].i))

        # Close animations in final layer
        while not self.anim.equals(Anim(self, None)):
            self.anim=self.anim.anim
            self.file.write("%sANIM_end\n" % self.anim.ins())

        self.file.write("\n# Built with Blender %4.2f. Exported with XPlane2Blender %s.\n" % (float(Blender.Get('version'))/100, __version__))
        self.file.close()

        if not n==len(offsets)==len(counts):
            raise ExportError('Bug - indices out of sync')
        
    #------------------------------------------------------------------------
    def sortLamp(self, object):

        (anim, mm)=self.makeAnim(object)

        if object.getType()=='Mesh':
            # This is actually a custom light - material has HALO set
            mesh=object.getData(mesh=True)
            mats=mesh.materials
            for f in mesh.faces:
                material=mats[f.mat]
                rgba=[material.R, material.G, material.B, material.alpha]
                mtex=material.getTextures()[0]
                if mtex:
                    uv1=UV(mtex.tex.crop[0], mtex.tex.crop[1])
                    uv2=UV(mtex.tex.crop[2], mtex.tex.crop[3])
                else:
                    uv1=UV(0,0)
                    uv2=UV(1,1)
                break

            # get RGBA and name properties
            dataref='NULL'
            for prop in object.getAllProperties():
                if prop.name in ['R','G','B','A']:
                    if prop.type in ['INT', 'FLOAT']:
                        rgba[['R','G','B','A'].index(prop.name)]=float(prop.data)
                    else:
                        raise ExportError('Unsupported data type for property "%s" in custom light "%s"' % (prop.name, object.name), [object])
                elif prop.name=='name':
                    if prop.type!='STRING': raise ExportError('Unsupported data type for dataref in custom light "%s"' % object.name, [object])
                    ref=prop.data.strip()
                    if ref in datarefs and datarefs[ref]:
                        (path, n)=datarefs[ref]
                        dataref=path+ref
                        if n!=9: raise ExportError('Dataref %s can\'t be used for custom lights' % dataref, [object])
                    else:
                        dataref=getcustomdataref(object, 'custom light', [ref])
                        
            for v in mesh.verts:
                light=Prim(object.Layer, self.findgroup(object), Prim.LIGHTS, False, DEFMAT, anim)
                light.i=CLIGHT(Vertex(v.co[0], v.co[1], v.co[2], mm),
                               rgba, material.haloSize, 
                               uv1, uv2, dataref)
                self.nlights.append(light)
            return

        light=Prim(object.Layer, self.findgroup(object), Prim.LIGHTS, False, DEFMAT, anim)

        lamp=object.getData()
        name=object.name
        special=0
        
        if lamp.getType() != Lamp.Types.Lamp:
            print 'Info:\tIgnoring Area, Spot, Sun or Hemi lamp "%s"' % name
            self.log.append(('Ignoring Area, Spot, Sun or Hemi lamp "%s"' % name, [object]))
            return
        
        if self.verbose:
            print 'Info:\tExporting Light "%s"' % name

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
        elif name in ['smoke_black', 'smoke_white']:
            light.i=SMOKE(Vertex(0,0,0, mm), name, lamp.energy)
            self.nlights.append(light)
            return            
        else:	# named light
            for prop in object.getAllProperties():
                if prop.name.lower()=='name': name=str(prop.data).strip()
            light.i=NLIGHT(Vertex(0,0,0, mm), name)
            self.nlights.append(light)
            return

        light.i=VLIGHT(Vertex(0,0,0, mm), c)
        self.lights.append(light)


    #------------------------------------------------------------------------
    def sortLine(self, object):
        if self.verbose:
            print 'Info:\tExporting Line "%s"' % object.name

        (anim, mm)=self.makeAnim(object)
        line=Prim(object.Layer, self.findgroup(object), Prim.LINES, False, DEFMAT, anim)

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

        if len(mesh.materials)>face.mat and mesh.materials[face.mat]:
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

        mesh=object.getData(mesh=True)
        mats=mesh.materials

        if object.getType()!='Mesh' or object.modifiers:
            # use dummy mesh with modifiers applied instead
            mesh=Mesh.New()
            mesh.getFromObject(object)
        
        (anim, mm)=self.makeAnim(object)
        hasanim=not anim.equals(Anim(self, None))
        nm=MatrixrotationOnly(mm, object)
        # Vertex order, taking into account negative scaling
        if object.SizeX*object.SizeY*object.SizeZ<0:
            seq=[[],[],[],[0,1,2],[0,1,2,3]]
        else:
            seq=[[],[],[],[2,1,0],[3,2,1,0]]

        if self.verbose:
            print 'Info:\tExporting Mesh "%s"' % object.name
                
        if self.debug:
            print 'Mesh "%s" %s faces' % (object.name, len(mesh.faces))

        group=self.findgroup(object)
        if self.iscockpit:
            surface=False
        else:
            for prop in object.getAllProperties():
                if prop.name.strip()=='surface':
                    if str(prop.data).strip() in Prim.SURFACES:
                        surface=prop.data.strip()
                        break
                    else:
                        raise ExportError('Invalid surface "%s" for face in mesh "%s"' % (prop.data, object.name), [object])
            else:
                surface=True

        # Optimisation: Children of animations might be dupes. This test only
        # looks for exact duplicates, but this can reduce vertex count by ~10%.
        twosideerr=[]
        harderr=[]
        degenerr=[]
        mode=Mesh.FaceModes.DYNAMIC
        if hasanim:
            animcands=list(self.animcands)	# List of candidate tris
            trino=0
            fudge=Vertex.LIMIT*10		# Be more lenient
            for f in mesh.faces:
                if mesh.faceUV: mode=f.mode
                n=len(f.v)
                if not n in [3,4]:
                    pass
                elif not (mode & Mesh.FaceModes.INVISIBLE):
                    for i in seq[n]:
                        nmv=f.verts[i]
                        vertex=Vertex(nmv.co[0], nmv.co[1], nmv.co[2], mm)
                        if not f.smooth:
                            norm=Vertex(f.no, nm)
                        else:
                            norm=Vertex(nmv.no, nm)
                        if mode & Mesh.FaceModes.TEX:
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
                for f in mesh.faces:
                    if mesh.faceUV: mode=f.mode
                    n=len(f.v)
                    if not n in [3,4]:
                        degenerr.append(f)
                    elif not (mode & Mesh.FaceModes.INVISIBLE):
                        if f.mat<len(mats) and mats[f.mat]:
                            material=mats[f.mat]
                            # diffuse, emission, shiny
                            mat=((material.R, material.G, material.B),
                                 (material.mirR*material.emit,
                                  material.mirG*material.emit,
                                  material.mirB*material.emit), material.spec)
                            if not mat in self.mats: self.mats.append(mat)
                        else:
                            mat=DEFMAT
                        face=Prim(object.Layer, group, 0, False, mat, anim)
           
                        if mode & Mesh.FaceModes.TEX:
                            if len(f.uv)!=n:
                                raise ExportError('Missing UV in mesh "%s"' % object.name, [object])
                            if f.transp == Mesh.FaceTranspModes.ALPHA:
                                face.flags|=Prim.ALPHA
        
                        if mode & Mesh.FaceModes.TWOSIDE:
                            face.flags|=Prim.TWOSIDE
                            twosideerr.append(f)
        
                        if not mode&Mesh.FaceModes.TILES or self.iscockpit:
                            face.flags|=Prim.NPOLY
                            
                        if self.iscockpit and mode&Mesh.FaceModes.TEX and f.image and 'panel.' in f.image.name.lower():
                            face.flags|=Prim.PANEL
                        elif object.Layer&1 and not (mode&Mesh.FaceModes.DYNAMIC or self.iscockpit):
                            face.surface=surface
                            harderr.append(f)

                        for i in range(n):
                            face.i.append(self.tris[animcands[0]+trino].i[i])
                            
                        self.tris.append(face)
                        trino+=1
                
                if degenerr and self.verbose:
                    print 'Info:\tIgnoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name)
                    self.log.append(('Ignoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name), (object, mesh, degenerr)))
                if harderr:
                    print 'Info:\tFound %s hard face(s) in mesh "%s"' % (len(harderr), object.name)
                    self.log.append(('Found %s hard face(s) in mesh "%s"' % (len(harderr), object.name), (object, mesh, harderr)))
                if twosideerr:
                    print 'Info:\tFound %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name)
                    self.log.append(('Found %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name), (object, mesh, twosideerr)))
                return

        # Either no animation, or no matching animation
        starttri=len(self.tris)
        # Optimisation: Build list of faces and vertices
        vti = [[] for i in range(len(mesh.verts))]	# indices into vt

        for f in mesh.faces:
            if mesh.faceUV: mode=f.mode
            n=len(f.v)
            if not n in [3,4]:
                degenerr.append(f)
            elif not (mode & Mesh.FaceModes.INVISIBLE):
                if f.mat<len(mats) and mats[f.mat]:
                    material=mats[f.mat]
                    # diffuse, emission, shiny
                    mat=((material.R, material.G, material.B),
                         (material.mirR*material.emit,
                          material.mirG*material.emit,
                          material.mirB*material.emit), material.spec)
                    if not mat in self.mats: self.mats.append(mat)
                else:
                    mat=DEFMAT
                face=Prim(object.Layer, group, 0, False, mat, anim)
   
                if mode & Mesh.FaceModes.TEX:
                    if len(f.uv)!=n:
                        raise ExportError('Missing UV for face in mesh "%s"' % object.name, (object, mesh, [f]))
                    if f.transp == Mesh.FaceTranspModes.ALPHA:
                        face.flags|=Prim.ALPHA

                if mode & Mesh.FaceModes.TWOSIDE:
                    face.flags|=Prim.TWOSIDE
                    twosideerr.append(f)

                if not mode&Mesh.FaceModes.TILES or self.iscockpit:
                    face.flags|=Prim.NPOLY
                    
                if self.iscockpit and mode&Mesh.FaceModes.TEX and f.image and 'panel.' in f.image.name.lower():
                    face.flags|=Prim.PANEL
                elif object.Layer&1 and not (mode&Mesh.FaceModes.DYNAMIC or self.iscockpit):
                    face.surface=surface
                    harderr.append(f)

                for i in seq[n]:
                    nmv=f.verts[i]
                    vertex=Vertex(nmv.co[0], nmv.co[1], nmv.co[2], mm)
                    if not f.smooth:
                        norm=Vertex(f.no, nm)
                    else:
                        norm=Vertex(nmv.no, nm)
                    if mode & Mesh.FaceModes.TEX:
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
            print 'Info:\tIgnoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name)
            self.log.append(('Ignoring %s degenerate face(s) in mesh "%s"' % (len(degenerr), object.name), (object, mesh, degenerr)))
        if harderr:
            print 'Info:\tFound %s hard face(s) in mesh "%s"' % (len(harderr), object.name)
            self.log.append(('Found %s hard face(s) in mesh "%s"' % (len(harderr), object.name), (object, mesh, harderr)))
        if twosideerr:
            print 'Info:\tFound %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name)
            self.log.append(('Found %s two-sided face(s) in mesh "%s"' % (len(twosideerr), object.name), (object, mesh, twosideerr)))


    #------------------------------------------------------------------------
    # Return name of group that this object belongs to
    def findgroup(self, ob):
        for group in self.groups:
            if ob in group.objects:
                return group
        return None
    
    #------------------------------------------------------------------------
    # Return (Anim object, Transformation for object relative to world/parent)
    def makeAnim(self, child):

        #return (Anim(None), mm)	# test - return frame 1 position

        anim=Anim(self, child)

        # Add parent anims first
        al=[]
        a=anim
        while not a.equals(Anim(self, None)):
            al.insert(0, a)
            a=a.anim

        Blender.Set('curframe', 1)
        #scene=Blender.Scene.GetCurrent()
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
            if a.t:
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
    def updateAttr(self, layer, group, anim, surface=None, mat=None, twoside=None, npoly=None, panel=None, alpha=None):
        # Write in sort order for readability

        if layer!=self.layer:
            # Reset all attributes
            while not self.anim.equals(Anim(self, None)):
                self.anim=self.anim.anim
                self.file.write("%sANIM_end\n" % self.anim.ins())

            self.surface=False
            self.mat=DEFMAT
            self.twoside=False
            self.npoly=True
            self.panel=False
            self.alpha=False
            self.group=None
                
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
            while not a.equals(Anim(self, None)):
                olda.insert(0, a)
                a=a.anim
            a=anim
            while not a.equals(Anim(self, None)):
                newa.insert(0, a)
                a=a.anim
            for i in range(len(olda)-1,-1,-1):
                if i>=len(newa) or not newa[i].equals(olda[i]):
                    olda.pop()
                    self.anim=self.anim.anim
                    self.file.write("%sANIM_end\n" % self.anim.ins())
        else:
            newa=olda=[]
    
        if self.group!=group:
            self.file.write("%s####_group\t%s\n" %(self.anim.ins(),group.name))
            self.group=group

        if npoly!=None:
            if self.npoly and not npoly:
                self.file.write("%sATTR_poly_os\t2\n" % self.anim.ins())
            elif npoly and not self.npoly:
                self.file.write("%sATTR_poly_os\t0\n" % self.anim.ins())
            self.npoly=npoly

        # alpha is implicit - doesn't appear in output file
        if alpha!=None:
            if self.alpha and not alpha:
                self.file.write("%s####_no_alpha\n" % self.anim.ins())
            elif alpha and not self.alpha:
                self.file.write("%s####_alpha\n" % self.anim.ins())
            self.alpha=alpha

        if panel!=None:
            if self.panel and not panel:
                self.file.write("%sATTR_no_cockpit\n" % self.anim.ins())
            elif panel and not self.panel:
                self.file.write("%sATTR_cockpit\n" % self.anim.ins())
            self.panel=panel

        for i in newa[len(olda):]:
            self.file.write("%sANIM_begin\n" % self.anim.ins())
            self.anim=i
            for (sh, d, v1, v2) in self.anim.showhide:
                self.file.write("%sANIM_%s\t%s %s\t%s\n" % (
                    self.anim.ins(), sh, v1, v2, d))
            if self.anim.t and not (self.anim.t[0].equals(Vertex(0,0,0)) and self.anim.t[1].equals(Vertex(0,0,0))):
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
                self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[0],
                    self.anim.a[0], self.anim.a[1],
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))
            elif len(self.anim.r)==2:
                self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[0],
                    self.anim.a[0], 0,
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))
                self.file.write("%sANIM_rotate\t%s\t%6.2f %6.2f\t%s %s\t%s\n"%(
                    self.anim.ins(), self.anim.r[1],
                    0, self.anim.a[1],
                    self.anim.v[0], self.anim.v[1], self.anim.dataref))

        if twoside!=None:
            if self.twoside and not twoside:
                self.file.write("%sATTR_cull\n" % self.anim.ins())
            elif twoside and not self.twoside:
                self.file.write("%sATTR_no_cull\n" % self.anim.ins())
            self.twoside=twoside

        if mat!=None:
            if self.mat!=mat and mat==DEFMAT:
                self.file.write("%sATTR_reset\n" % self.anim.ins())
            else:
                # diffuse, emission, shiny
                if self.mat[0]!=mat[0]:
                    self.file.write("%sATTR_diffuse_rgb\t%6.3f %6.3f %6.3f\n" % (self.anim.ins(), mat[0][0], mat[0][1], mat[0][2]))
                if self.mat[1]!=mat[1]:
                    self.file.write("%sATTR_emission_rgb\t%6.3f %6.3f %6.3f\n" % (self.anim.ins(), mat[1][0], mat[1][1], mat[1][2]))
                if self.mat[2]!=mat[2]:
                    self.file.write("%sATTR_shiny_rat\t%6.3f\n" % (self.anim.ins(), mat[2]))
            self.mat=mat

        if surface!=None:
            if self.surface and not surface:
                self.file.write("%sATTR_no_hard\n" % self.anim.ins())
            elif surface and self.surface!=surface:
                if surface==True:
                    self.file.write("%sATTR_hard\n" % self.anim.ins())
                else:
                    self.file.write("%sATTR_hard\t%s\n" % (self.anim.ins(), surface))
            self.surface=surface


#------------------------------------------------------------------------
class Anim:
    def __init__(self, expobj, child, bone=None):
        self.dataref=None	# None if null
        self.r=[]	# 0, 1 or 2 rotation vectors
        self.a=[]	# rotation angles (iff self.r)
        self.t=[]	# translation
        self.v=[0,1]	# dataref value
        self.showhide=[]	# show/hide values (show/hide, name, v1, v2)
        self.anim=None	# parent Anim

        if not child:
            return	# null

        object=child.parent	# child is lamp/mesh. object is parent armature
        if not object or object.getType()!='Armature':
            return

        if Blender.Get('version')<240:
            raise ExportError('Blender version 2.40 or later required for animation')

        #if object.parent:
        #    raise ExportError('Armature "%s" has a parent; this is not supported. Use multiple bones within a single armature to represent complex animations.' % object.name, [object])
                
        if not bone:
            bonename=child.getParentBoneName()
            if not bonename: raise ExportError('%s "%s" has an armature as its parent. Make "%s" the child of a bone' % (child.getType(), child.name, child.name), [child])
            bones=object.getData().bones
            if bonename in bones.keys():
                bone=bones[bonename]
            else:
                raise ExportError('%s "%s" has a deleted bone "%s" as its parent. Either make "%s" the child of an existing bone, or clear its parent' % (child.getType(), child.name, bonename, child.name), [child])

        if bone.parent:
            #print "bp", child, bone.parent
            self.anim=Anim(expobj, child, bone.parent)
        elif object.parent and object.parent.getType()=='Armature':
            # child's parent armature is itself parented to an armature
            bonename=object.getParentBoneName()
            if not bonename: raise ExportError('Bone "%s" has an armature as its parent. Make "%s" the child of another bone' % (bone.name, bone.name), [child])
            bones=object.parent.getData().bones
            if bonename in bones.keys():
                parentbone=bones[bonename]
            else:
                raise ExportError('%s "%s" has a deleted bone "%s" as its parent. Either make "%s" the child of an existing bone, or clear its parent' % (child.getType(), child.name, bonename, child.name), [child])
            #print "ob", object, parentbone
            self.anim=Anim(expobj, object, parentbone)
        else:
            self.anim=Anim(expobj, None)

        if not bone.parent:
            # Hide/show values if eldest bone in its armature
            vals={}
            for prop in object.getAllProperties():
                propname=prop.name.strip()
                for suffix in ['_hide_v', '_show_v']:
                    if not (suffix) in propname: continue
                    digit=propname[propname.index(suffix)+7:]
                    if not digit.isdigit() or not int(digit)&1: continue
                    (ref, v)=self.getdataref(object, propname[:propname.index(suffix)], suffix[:-2], int(digit))
                    if v: self.showhide.append((suffix[1:5],ref,v[0],v[1]))

        #print "ac", object, bone.name, object.getAction(), object.getAction().getAllChannelIpos()[bone.name]
        if not (object.getAction() and
                object.getAction().getAllChannelIpos().has_key(bone.name)):
            print 'Warn:\tYou haven\'t created any animation keys for bone "%s" in armature "%s". Skipping this bone.' % (bone.name, object.name)
            expobj.log.append(('Ignoring bone "%s" in armature "%s" - you haven\'t created any animation keys' % (bone.name, object.name), [object]))

            if self.showhide:
                # Create a dummy animation to hold hide/show values
                self.dataref='no_ref'	# mustn't eval to False
                self.t=[Vertex(0,0,0),Vertex(0,0,0)]
            elif bone.parent:
                foo=Anim(expobj, child, bone.parent)
                self.dataref=foo.dataref
                self.r=foo.r
                self.a=foo.a
                self.t=foo.t
                self.v=foo.v
                self.anim=foo.anim
            else:
                self.dataref=None	# is null
            return

        (self.dataref, self.v)=self.getdataref(object, bone.name, '', 1)
        ipo=object.getAction().getAllChannelIpos()[bone.name]

        scene=Blender.Scene.GetCurrent()
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
        
        # Need to unset resting position of parent armature
        object.getData().restPosition=False
        # But grandparent armature (if any) need to be resting, since
        # getMatrix('localspace') doesn't account for rotation due to pose
        a=object.parent
        while a:
            a.getData().restPosition=True
            a=a.parent

        for frame in [1,2]:
            Blender.Set('curframe', frame)
            #scene.update(1)
            #scene.makeCurrent()	# see Blender bug #4696
            mm=object.getMatrix('worldspace')
            # mm.rotationPart() scaled to be unit size for rotation axis
            rm=MatrixrotationOnly(mm, object)
            
            if (not (bone.parent and Armature.CONNECTED in bone.options) and
                ipo.getCurve('LocX') and
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
            while not anim.equals(Anim(expobj, None)):
                t=t-anim.t[0]	# mesh location is relative to first frame
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

        a=object.parent
        while a:
            a.getData().restPosition=False
            a=a.parent


    #------------------------------------------------------------------------
    def getdataref(self, object, name, suffix, first):
        if not suffix:
            vals=[0,1]
            thing='bone in armature' 
        else:
            vals=[None,None]
            thing='property in armature'
            
        l=name.find('.')
        if l!=-1: name=name[:l]
        name=name.strip()
        # split name into ref & idx
        l=name.find('[')
        if l!=-1 and not name in datarefs:
            ref=name[:l].strip()
            idx=name[l+1:-1]
            if name[-1]!=']' or not idx or not idx.isdigit():
                raise ExportError('Malformed dataref index "%s" in bone "%s" in armature "%s"' % (name[l:], name, object.name), [object])
            idx=int(idx)
            seq=[ref, name]
        else:
            ref=name
            idx=None
            seq=[ref]

        props=object.getAllProperties()

        if ref in datarefs and datarefs[ref]:
            (path, n)=datarefs[ref]
            dataref=path+name
            if n==0:
                raise ExportError('Dataref %s can\'t be used for animation' % path+ref, [object])
            elif n==1 and idx!=None:
                raise ExportError('Dataref %s is not an array. Rename the %s to "%s"' % (path+ref, thing, ref), [object])
            elif n!=1 and idx==None:
                raise ExportError('Dataref %s is an array. Rename the %s to "%s[0]" to use the first value, etc' % (path+ref, thing, ref), [object])
            elif n!=1 and idx>=n:
                raise ExportError('Dataref %s has usable values from [0] to [%d]; but you specified [%d]' % (path+ref, n-1, idx), [object])
        else:
            dataref=getcustomdataref(object, thing, seq)

        # dataref values v1 & v2
        for tmpref in seq:
            for val in [first,first+1]:
                valstr="%s%s_v%d" % (tmpref, suffix, val)
                for prop in object.getAllProperties():
                    if prop.name.strip()==valstr:
                        if prop.type=='INT':
                            vals[val-first]=prop.data
                        elif prop.type=='FLOAT':
                            vals[val-first]=round(prop.data, Vertex.ROUND)
                        else:
                            raise ExportError('Unsupported data type for "%s" in armature "%s"' % (valstr, object.name), [object])
        if vals[0]==None or vals[1]==None: vals=None
        return (dataref, vals)


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
        if self.showhide!=b.showhide:
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
        while not anim.equals(Anim(self, None)):
            t=t+"\t"
            anim=anim.anim
        return t


#------------------------------------------------------------------------
def getcustomdataref(object, thing, names):
    dataref=None
    props=object.getAllProperties()
    for tmpref in names:
        for prop in props:
            if prop.name.strip()==tmpref:
                # custom dataref
                if prop.type=='STRING':
                    path=prop.data.strip()
                    if path and path[-1]!='/': path=path+'/'
                    dataref=path+names[-1]
                else:
                    raise ExportError('Unsupported data type for full name of custom dataref "%s" in armature "%s"' % (names[0], object.name), [object])
                break
    if not dataref:
        if names[0] in datarefs:
            raise ExportError('Dataref %s is ambiguous. Add a new string property named %s with the path name of the dataref that you want to use' % (names[0], names[0]), [object])
        else:
            raise ExportError('Unrecognised dataref "%s" for %s "%s"' % (names[0], thing, object.name), [object])
    return dataref


#------------------------------------------------------------------------
if Window.EditMode(): Window.EditMode(0)
try:
    obj=None
    scene = Blender.Scene.GetCurrent()

    baseFileName=Blender.Get('filename')
    l = baseFileName.lower().rfind('.blend')
    if l==-1: raise ExportError('Save this .blend file first')
    baseFileName=baseFileName[:l]
    datarefs=getDatarefs()
    obj=OBJexport8(baseFileName+'.obj')
    obj.export(scene)
except ExportError, e:
    for o in scene.objects: o.select(0)
    if e.objs:
        layers=[]
        if isinstance(e.objs, tuple):
            (o,mesh,faces)=e.objs
            o.select(1)
            layers=o.layers
            for f in mesh.faces: f.sel=0
            if faces:
                for f in faces: f.sel=1
                for i in range(len(mesh.faces)):
                    if mesh.faces[i]==faces[0]:
                        mesh.activeFace=i
                        break
        else:
            for o in e.objs:
                o.select(1)
                for layer in o.layers:
                    if (layer<=3 or not o.Layers&7) and not layer in layers:
                        layers.append(layer)
        Window.ViewLayers(layers)
        Window.RedrawAll()
    if e.msg:
        Window.WaitCursor(0)
        Window.DrawProgressBar(0, 'ERROR')
        print "ERROR:\t%s.\n" % e.msg
        Draw.PupMenu("ERROR%%t|%s" % e.msg)
        Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
except IOError, e:
    Window.WaitCursor(0)
    Window.DrawProgressBar(0, 'ERROR')
    print "ERROR:\t%s\n" % e.strerror
    Draw.PupMenu("ERROR%%t|%s" % e.strerror)
    Window.DrawProgressBar(1, 'ERROR')
    if obj and obj.file: obj.file.close()
