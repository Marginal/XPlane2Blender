#!BPY
""" Registration info for Blender menus:
Name: ' X-Plane v7 Object (.obj)'
Blender: 240
Group: 'Export'
Tooltip: 'Export to X-Plane v7 format object (.obj)'
"""
__author__ = "Jonathan Harris"
__url__ = ("Script homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.18"
__bpydoc__ = """\
This script exports scenery created in Blender to X-Plane v7 .obj
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
# 2004-02-01 v1.00
#  - First public version.
#
# 2004-02-04 v1.10
#  - Updated for Blender 2.32.
#
# 2004-02-05 v1.11
#  - Removed dependency on Python installation.
#
# 2004-02-08 v1.12
#  - Fixed filename bug when texture file is a png.
#
# 2004-02-09 v1.13
#  - Fixed lack of comment bug on v7 objects.
#
# 2004-02-29 v1.20
#  - Emulate Lines with faces.
#  - Automatically generate strips where possible for faster rendering.
#
# 2004-03-24 v1.30
#  - Reduced duplicate vertex limit from 0.25 to 0.1 to handle smaller objects
#  - Sort faces by type for correct rendering in X-Plane. This fixes bugs with
#    alpha and no_depth faces.
#
# 2004-04-10 v1.40
#  - Reduced duplicate vertex limit to 0.01 to handle imported objects.
#  - Support 3 LOD levels: 1000,4000,10000.
#
# 2004-08-22 v1.50
#  - Reversed meaning of DYNAMIC flag, since it is set by default when
#    creating new faces in Blender.
#
# 2004-08-28 v1.60
#  - Added support for double-sided faces.
#
# 2004-08-28 v1.61
#  - Requires Blender 234 due to changed layer semantics of Blender fix #1212.
#  - Display number of X-Plane objects on import and export.
#
# 2004-08-29 v1.62
#  - Light and Line colours are floats
#  - Don't generate ATTR_no_depth - its meaning changed from X-Plane
#    7.61 and it no longer helps with Z-buffer thrashing.
#
# 2004-08-30 v1.63
#  - Work round X-Plane 7.x tri_fan normal bug by disabling generation of
#    "unclosed" tri_fans.
#
# 2004-09-04 v1.71
#  - Since ATTR_no_depth is broken, changed output ordering to make no_depth
#    faces come after normal faces. This slightly improves rendering maybe.
#
# 2004-09-10 v1.72
#  - Fixed bug with exporting flashing lights.
#
# 2004-10-10 v1.73
#  - Fixed missing data in tri_fans when triangle vertices are within
#    duplicate vertex limit, which led to corrupt output file.
#  - Reduced duplicate vertex limit to 0.001 for small objects eg cockpits.
#
# 2004-10-17 v1.74
#  - Warn if objects present in layers other than 1-3, suggested by
#    Hervé Duchesne de Lamotte.
#
# 2004-11-01 v1.80
#  - Support for "quad_cockpit" using "Text" button.
#
# 2004-11-14 v1.81
#  - Ignore use of "Text" button; cockpit panels now detected by texture name.
#  - Panel polygons must go last in file.
#  - Prettified output slightly.
#
# 2004-11-22 v1.82
#  - Fix for LOD detection when objects exist outside levels 1-3.
#  - tri_fan disable hack from v1.63 not applied to smooth meshes - normal
#    bug appears to be less noticable with smooth meshes.
#
# 2004-12-10 v1.84
#  - Default smoothing state appears different between cockpits and scenery
#    so explicitly set smoothing state at start of file.
#
# 2004-12-28 v1.85
#  - Fix formatting bug in vertex output introduced in v1.81.
#
# 2004-12-29 v1.86
#  - Removed residual broken support for exporting v6 format.
#  - Work round X-Plane 8.x limitation where quad_cockpit polys must
#    start with the top or bottom left vertex.
#  - Check that quad_cockpit texture t < 768.
#  - Work round X-Plane 7.6x bug where default poly_os level appears to be
#    undefined. Problem appears fixed in v8.0x.
#
# 2004-12-29 v1.87
#  - Really fix quad_cockpit left vertex thing.
#
# 2004-12-30 v1.88
#  - Fix quad_cockpit vertex order for non-squarish textures. Still doesn't
#    handle mirrored textures.
#  - Suppress LODs if making a cockpit object.
#  - Tweaked tri_fans again - generate tri_fans for >=8 faces and either
#    closed or smoothed - helps with nose of imported aircraft.
#  - Calculate quad orientation more accurately during strip generation -
#    helps to smooth correctly the nose and tail of imported aircraft.
#  - Remove sort on no_depth/TILES - it hasn't done anything useful since 1.62.
#
# 2005-01-09 v1.89
#  - Faster strip creation algorithm - only looks in same mesh for strips.
#  - Turn texture warnings into errors and raise before creating output file.
#  - Relaxed restriction on quad_cockpit textures - only one has to be within
#    1024x768.
#  - Also recognise cockpit_inn and cockpit_out as cockpit objects.
#
# 2005-01-15 v1.90
#  - Add variable to control whether to generate strips.
#
# 2005-02-08 v1.91
#  - Fixed nannying bug with panel textures with height < 1024.
#
# 2005-04-07 v1.92
#  - Fixed bug with panels present in layers 2&3.
#  - Fixed hang with degenerate meshes in cockpits.
#
# 2005-04-24 v2.00
#  - Don't output LOD statements for empty LODs.
#  - Optimise output order to minimise OpenGL state changes.
#  - Be much less verbose.
#
# 2005-05-09 v2.01
#  - Fix up relative image pathnames to avoid spurious duplicates.
#
# 2005-05-11 v2.03
#  - Fix stupid panel bug.
#
# 2005-05-13 v2.04
#  - Allow panels to be two-sided.
#
# 2005-09-23 v2.10
#  - Fix for lines exported outside LODs
#
# 2006-01-05 v2.16
#  - Fix for relative texture paths.
#

#
# X-Plane renders polygons in scenery files mostly in the order that it finds
# them - it detects use of alpha and deletes wholly transparent polys, but
# doesn't sort by Z-buffer order.
#
# Panel polygons must come last (at least in v8.00-8.20) for LIT textures to
# work for non-panel polygons. The last polygon in the file must not be a
# quad_cockpit with texture outside 1024x768 else everything goes wierd.
#
# So we have to sort on export. The algorithm below isn't guaranteed to
# produce the right result in all cases, but seems to work OK in practice:
#
#  1. Output header and texture file name.
#  2. For each layer:
#     3. Output lights and lines in the order that they're found.
#        Build up list of meshes, each mesh listing faces and vertices.
#     4. Output mesh faces in all combinations of the following attributes:
#        - HARD
#        - TWOSIDE
#        - FLAT
#        - ALPHA
#        - PANEL
#        For each attribute, sort on polygon type.
#

import sys
import Blender
from Blender import NMesh, Lamp, Image, Draw, Window
from XPlaneUtils import Vertex, UV, Face
from XPlaneExport import *
#import time

class Mesh:
    def __init__(self, name):
        self.name=name
        self.faces=[]
        self.verts=[]


#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        self.optimise=1	# whether to make strips, sort faces etc
        
        #--- class private don't touch ---
        self.file=None
        self.filename=filename
        self.iscockpit=((filename.lower().find("_cockpit.obj") != -1) or
                        (filename.lower().find("_cockpit_inn.obj") != -1) or
                        (filename.lower().find("_cockpit_out.obj") != -1))
        self.layermask=1
        self.havepanel=False
        self.texture=None
        self.linewidth=0.1
        self.nprim=0		# Number of X-Plane primitives exported

        # attributes controlling export
        self.hard=False
        self.twoside=False
        self.flat=False		# >=7.30 defaults to smoothed
        self.alpha=False	# implicit - doesn't appear in output file
        self.panel=False
        self.layer=0

    #------------------------------------------------------------------------
    def export(self, scene):
        theObjects = []
        theObjects = scene.getChildren()

        print "Starting OBJ export to " + self.filename
        if not checkFile(self.filename):
            return

        Blender.Window.WaitCursor(1)
        Window.DrawProgressBar(0, "Examining textures")
        (self.texture,self.havepanel,self.layermask)=getTexture(theObjects,
                                                                self.layermask,
                                                                self.iscockpit,
                                                                7)
        if self.havepanel:
            self.iscockpit=True
            self.layermask=1
        
        #clock=time.clock()	# Processor time

        self.file = open(self.filename, "w")
        self.writeHeader ()
        self.writeObjects (theObjects)
        checkLayers (theObjects, self.iscockpit)
        self.file.close ()
        
        Window.DrawProgressBar(1, "Finished")
        #print "%s CPU time" % (time.clock()-clock)
        print "Finished - exported %s primitives\n" % self.nprim

    #------------------------------------------------------------------------
    def writeHeader (self):
        if Blender.sys.progname.find("blender.app")!=-1:
            systype='A'
        else:
            systype='I'
        self.file.write("%s\n700\t// \nOBJ\t// \n\n" % systype)
        if self.texture:
            self.file.write("%s\t\t// Texture\n\n" % self.texture)
        else:	# Barfs if no texture specified
            self.file.write("none\t\t\t// Texture\n\n")            
        if not self.iscockpit:
            self.file.write("ATTR_poly_os 0\t\t// fix for versions < 8.20\n\n")

    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):

        if self.layermask==1:
            lseq=[1]
        else:
            lseq=[1,2,4]

        # Count the objects
        nobj=0
        objlen=1
        for layer in lseq:
            for object in theObjects:
                if object.Layer&layer:
                    objlen=objlen+1
        
        if self.optimise:
            npasses=Face.BUCKET+1
        else:
            npasses=1
        objlen=objlen*(1+npasses)

        for layer in lseq:
            meshes=[]

            self.updateLayer(layer)

            # 1st pass: Output Lamps and Lines, build meshes
            for o in range (len(theObjects)-1,-1,-1):
                object=theObjects[o]
                if not object.Layer&layer:
                    continue
                
                Window.DrawProgressBar(float(nobj)/objlen,
                                       "Exporting %s%% ..." % (
                    nobj*100/objlen))
                nobj=nobj+1

                objType=object.getType()
                if objType == "Mesh":
                    if isLine(object, self.linewidth):
                        self.writeLine(object)
                    else:
                        meshes.append(self.sortMesh(object, layer))
                elif objType == "Lamp":
                    self.writeLamp(object)
                else:
                    print "Warn:\tIgnoring %s \"%s\"" % (objType.lower(),
                                                         object.name)

            # Hack! Find a kosher panel texture and put it last
            if self.havepanel:
                panelsorted=0
                i=len(meshes)-1
                while not panelsorted:
                    if meshes[i].faces:
                        for j in range(len(meshes[i].faces)):
                            if meshes[i].faces[j].kosher:
                                mesh=Mesh(meshes[i].name)
                                mesh.faces.append(meshes[i].faces[j])
                                meshes[i].faces[j]=0	# Remove original face
                                meshes.append(mesh)
                                panelsorted=1
                                break
                    i=i-1

            # 2nd to 2**n+1th pass: Output meshes
            for passno in range(npasses):
                strips=[]
                for i in range(len(meshes)):
                    Window.DrawProgressBar(float(nobj)/objlen,
                                           "Exporting %s%% ..." % (
                        nobj*100/objlen))
                    nobj=nobj+1

                    if meshes[i]:
                        self.makeStrips(strips, meshes[i], passno)

                for (strip, firstvertex, name) in strips:
                    if len(strip)>1 and len(strip[0].v)==3:
                        self.writeStrip(strip, firstvertex, name)
                for (strip, firstvertex, name) in strips:
                    if len(strip)==1 and len(strip[0].v)==3:
                        self.writeStrip(strip, firstvertex, name)
                for (strip, firstvertex, name) in strips:
                    if len(strip)>1 and len(strip[0].v)==4:
                        self.writeStrip(strip, firstvertex, name)
                for (strip, firstvertex, name) in strips:
                    if len(strip)==1 and len(strip[0].v)==4:
                        self.writeStrip(strip, firstvertex, name)
                    
        self.file.write("end\t\t\t// eof\n\n")
        self.file.write("// Built with Blender %4.2f. Exported with XPlane2Blender %s.\n" % (float(Blender.Get('version'))/100, __version__))

    #------------------------------------------------------------------------
    def writeLamp(self, object):
        lamp=object.getData()
        name=lamp.getName()
        special=0
        
        if lamp.getType() != Lamp.Types.Lamp:
            print "Info:\tIgnoring Area, Spot, Sun or Hemi lamp \"%s\"" % name
            return
        
        if self.verbose:
            print "Info:\tExporting Light \"%s\"" % name

        lname=name.lower()
        c=[0,0,0]
        if lname.find("pulse")!=-1:
            c[0]=c[1]=c[2]=99
            special=1
        elif lname.find("strobe")!=-1:
            c[0]=c[1]=c[2]=98
            special=1
        elif lname.find("traffic")!=-1:
            c[0]=c[1]=c[2]=97
            special=1
        elif lname.find("flash")!=-1:
            c[0]=-lamp.col[0]*10
            c[1]=-lamp.col[1]*10
            c[2]=-lamp.col[2]*10
        else:
            c[0]=lamp.col[0]*10
            c[1]=lamp.col[1]*10
            c[2]=lamp.col[2]*10

        v=Vertex(0,0,0, object.getMatrix())
        self.file.write("light\t\t\t// %s\n" % name)
        if special:
            self.file.write("%s\t%2d     %2d     %2d\n\n" % (v,c[0],c[1],c[2]))
        else:
            self.file.write("%s\t%-6s %-6s %-6s\n\n" % (
                v, round(c[0],3), round(c[1],3), round(c[2],3)))
        self.nprim+=1


    #------------------------------------------------------------------------
    def writeLine(self, object):
        name=object.name
        if self.verbose:
            print "Info:\tExporting Line \""+name+"\""

        mesh=object.getData()
        mm=object.getMatrix()
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
            c=[mesh.materials[face.mat].R*10,
               mesh.materials[face.mat].G*10,
               mesh.materials[face.mat].B*10,]
        else:
            c=[5,5,5]
    
        self.file.write("line\t\t\t// %s\n" % name)
        self.file.write("%s\t%-6s %-6s %-6s\n" % (
            v1, round(c[0],3), round(c[1],3), round(c[2],3)))
        self.file.write("%s\t%-6s %-6s %-6s\n\n" % (
            v2, round(c[0],3), round(c[1],3), round(c[2],3)))
        self.nprim+=1


    #------------------------------------------------------------------------
    def sortMesh(self, object, layer):

        nmesh=object.getData()
        mm=object.getMatrix()

        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(nmesh.faces))

        # Build list of faces and vertices
        twosideerr=0
        harderr=0
        mesh=Mesh(object.name)
        for f in nmesh.faces:
            n=len(f.v)
            if not n in [3,4]:
                if self.verbose:
                    print "Warn:\tIgnoring degenerate face in mesh \"%s\"" % (
                        object.name)
            else:
                face=Face()
                
                if f.mode & NMesh.FaceModes.TEX:
                    if len(f.uv)!=n:
                        raise ExportError("Missing UV in mesh \"%s\"" % object.name)
                    if f.transp == NMesh.FaceTranspModes.ALPHA:
                        face.flags|=Face.ALPHA

                #if f.mode & NMesh.FaceModes.TILES:
                #    face.flags|=Face.TILES

                if f.mode & NMesh.FaceModes.TWOSIDE:
                    face.flags|=Face.TWOSIDE
                    twosideerr=twosideerr+1

                if not f.smooth:
                    face.flags|=Face.FLAT

                if f.image and f.image.name.lower().find("panel.")!=-1:
                    face.flags|=Face.PANEL
                    try:
                        height=f.image.getSize()[1]
                    except RuntimeError:
                        raise ExportError("Can't load instrument panel texture file")
                    for uv in f.uv:
                        if (uv[0]<0.0 or uv[0]>1.0 or
                            (1-uv[1])*height>768 or uv[1]>1.0):
                            break
                    else:
                        face.kosher=1
                elif (n==4 and
                      not (f.mode & NMesh.FaceModes.DYNAMIC) and
                      not self.iscockpit and
                      layer==1):
                    face.flags|=Face.HARD
                    harderr=harderr+1

                v=[]
                for i in range(n):
                    vertex=Vertex(f.v[i][0],f.v[i][1],f.v[i][2], mm)
                    for q in mesh.verts:
                        if vertex.equals(q):
                            q.x = (q.x + vertex.x) / 2
                            q.y = (q.y + vertex.y) / 2
                            q.z = (q.z + vertex.z) / 2
                            face.addVertex(q)
                            break
                    else:
                        mesh.verts.append(vertex)
                        face.addVertex(vertex)

                    if f.mode & NMesh.FaceModes.TEX:
                        face.addUV(UV(f.uv[i][0],f.uv[i][1]))
                    else:	# File format requires something - using (0,0)
                        face.addUV(UV(0,0))

                # merge duplicate vertices in this face
                i=0
                while i < len(face.v):
                    for j in range (len(face.v)):
                        if i!=j and face.v[i]==face.v[j]:
                            face.v.pop(j)
                            face.uv[i].s = (face.uv[i].s + face.uv[j].s) / 2
                            face.uv[i].t = (face.uv[i].t + face.uv[j].t) / 2
                            face.uv.pop(j)
                            break
                    i+=1

                # Disappeared!
                if len(face.v) < 3:
                    if self.verbose:
                        print "Warn:\tIgnoring degenerate face in mesh \"%s\"" % (object.name)
                    continue

                # Add this face to the list and add pointers from the vertices
                mesh.faces.append(face)
                for vertex in face.v:
                    vertex.addFace(len(mesh.faces)-1)
                
                if self.debug: print face

        if harderr:
            print "Info:\tFound %s hard face(s) in mesh \"%s\"" % (
                harderr, object.name)
        if twosideerr:
            print "Info:\tFound %s two-sided face(s) in mesh \"%s\"" % (
                twosideerr, object.name)

        return mesh

    #------------------------------------------------------------------------
    def makeStrips(self, strips, mesh, bucket):

        # Identify strips
        faces=mesh.faces
        verts=mesh.verts
        for faceindex in range(len(faces)):

            if (faces[faceindex] and not self.optimise):
                # Just write
                self.writeStrip([faces[faceindex]], 0, mesh.name)
                
            elif (faces[faceindex] and
                (faces[faceindex].flags&Face.BUCKET) == bucket):

                startface=faces[faceindex]
                strip=[startface]
                faces[faceindex]=0	# take face off list
                firstvertex=0
                        
                if (startface.flags & Face.HARD or
                    startface.flags & Face.PANEL):
                    # Can't be part of a Quad_Strip
                    strips.append((strip, 0, mesh.name))

                elif len(startface.v)==3:

                    # First look for a tri_fan.
                    # Vertex which is member of most triangles is centre.
                    tris=[]
                    for v in startface.v:
                        tri=0
                        for i in v.faces:
                            if  (faces[i] and len(faces[i].v) == 3 and
                                 (faces[i].flags&Face.BUCKET) == bucket):
                                tri=tri+1
                        tris.append(tri)
                    if tris[0]>=tris[1] and tris[0]>=tris[2]:
                        c=0
                    elif tris[1]>=tris[2]:
                        c=1
                    else:
                        c=2
                    firstvertex=(c-1)%3
                    if self.debug: print "Start fan, centre=%s:\n%s" % (
                        c, startface)

                    tri_inds=[faceindex]
                    for o in [0,2]:
                        # vertices must be in clockwise order
                        if self.debug: print "Order %s" % o
                        of=startface
                        v=(c+o)%3
                        while 1:
                            (nf,i)=self.findFace(faces,of,v)
                            if nf>=0:
                                of=faces[nf]
                                if self.debug: print of
                                if o==0:
                                    strip.append(of)
                                    tri_inds.append(nf)
                                    v=(i+1)%3
                                else:
                                    strip.insert(0, of)
                                    tri_inds.insert(0, nf)
                                    v=(i-1)%3
                                    firstvertex=v
                                faces[nf]=0  # take face off list
                            else:
                                break

                    # tri_fans are rendered incorrectly (wrong apex
                    # normal) under some situations. So only make a
                    # tri_fan if enough vertices and either smoothed
                    # or closed.
                    if len(strip)>=8:	# strictly >2
                        # closed if first and last faces share two vertices
                        common=0
                        for i in range(3):
                            for j in range(3):
                                if strip[0].v[i].equals(strip[-1].v[j]):
                                    common+=1
                        if common==2 or not startface.flags&Face.FLAT:
                            if self.verbose:
                                print "Info:\tFound Tri_Fan    of %2d faces in Mesh \"%s\"" % (len(strip), mesh.name)
                            strips.append((strip, firstvertex, mesh.name))
                            continue
                        elif self.debug:
                            print "Not closed (%s)" % common

                    # Didn't find a tri_fan, restore deleted faces
                    for i in range(len(strip)):
                        faces[tri_inds[i]]=strip[i]
                    
                    strip=[startface]
                    firstvertex=0

                    # Look for a tri_strip
                    # XXXX ToDO
                    
                    if len(strip)>1 and self.verbose:
                        print "Info:\tFound Tri_Strip  of %2d faces in Mesh \"%s\"" % (len(strip), mesh.name)
                    
                    strips.append((strip, firstvertex, mesh.name))
                    
                elif len(startface.v)==4:
                    # Find most horizontal edge
                    miny=sys.maxint
                    for i in range(4):
                        q=(startface.v[i]-startface.v[(i+1)%4]).normalize()
                        if abs(q.y)<miny:
                            sv=i
                            miny=abs(q.y)
                    
                    if self.debug: print "Start strip, edge=%s,%s:\n%s" % (
                        sv, (sv+1)%4, startface)

                    # Strip could maybe go two ways
                    if not startface.flags&Face.FLAT:
                        # Vertically then Horizontally for fuselages
                        seq=[0,1]
                    else:
                        # Horizontally then Vertically
                        seq=[1,0]
                    for hv in seq:	# rotate 0 or 90
                        firstvertex=(sv+2+hv)%4
                        for o in [0,2]:
                            # vertices must be in clockwise order
                            if self.debug: print "Order %s" % (o+hv)
                            of=startface
                            v=(sv+o+hv)%4
                            while 1:
                                (nf,i)=self.findFace(faces,of,v)
                                if nf>=0:
                                    of=faces[nf]
                                    if self.debug: print of
                                    v=(i+2)%4
                                    if o==0:
                                        strip.append(of)
                                    else:
                                        strip.insert(0, of)
                                        firstvertex=v
                                    faces[nf]=0  # take face off list
                                else:
                                    break
                        # not both horiontally and vertically
                        if len(strip)>1:
                            break

                    if len(strip)>1 and self.verbose:
                        print "Info:\tFound Quad_Strip of %2d faces in Mesh \"%s\"" % (len(strip), mesh.name)
                    strips.append((strip, firstvertex, mesh.name))
                

    #------------------------------------------------------------------------
    # Return index of a face which has the same number of edges, same flags,
    # has v and v+1 as vertices and faces the same way as the supplied face.
    def findFace (self,faces,face,v):
        n=len(face.v)
        v1=face.v[v]
        v2=face.v[(v+1)%n]
        uv1=face.uv[v]
        uv2=face.uv[(v+1)%n]
        for faceindex in v1.faces:
            f=faces[faceindex]
            if f and f!=face and f.flags==face.flags and len(f.v)==n:
                for i in range(n):
                    if  (f.v[i]==v2 and
                         f.v[(i+1)%n]==v1 and
                         f.uv[i].equals(uv2) and
                         f.uv[(i+1)%n].equals(uv1)):
                        return (faceindex,i)
        return (-1,-1)

    #------------------------------------------------------------------------
    # Write out a strip of Tris or Quads
    # Assumes all faces face the same way
    # Assumes whole strip is either Tris or Quads, not mix of both
    # Assumes whole strip is either smooth or flat, not mix of both
    # Assumes whole strip is either depth tested or not, not mix of both
    # Assumes that any "hard" or "panel" faces are in a strip of length 1
    def writeStrip (self, strip, firstvertex, name):
        
        face=strip[0]
        n=len(face.v)
        self.updateAttr(face.flags&Face.HARD, face.flags&Face.TWOSIDE,
                        face.flags&Face.FLAT, face.flags&Face.ALPHA,
                        face.flags&Face.PANEL)
        
        if (len(strip))==1:
            # Oh for fuck's sake. X-Plane 8.00-8.06 loses the plot unless
            # quad_cockpit polys start with the top or bottom left vertex.
            # We'll choose the vertex with smallest s.
            mins=sys.maxint
            for i in range(n):
                if face.uv[i].s < mins:
                    mins=face.uv[i].s
                    start=i
                            
            if (n==3):
                self.file.write ("tri\t")
            elif (face.flags & Face.PANEL):
                self.file.write ("quad_cockpit")
            elif (face.flags & Face.HARD):	# Note can't be both panel and hard
                self.file.write ("quad_hard")
            else:
                self.file.write ("quad\t")
            self.file.write("\t\t// %s\n" % name)

            for i in range(start, start-n, -1):
                self.file.write("%s\t%s\n" % (face.v[i%n], face.uv[i%n]))

        else:	# len(strip)>1
            if self.debug:
                for f in strip:
                    print f

            if n==3:
                self.file.write ("tri_fan %s" % (len(strip)+2))
            else:
                self.file.write ("quad_strip %s" % ((len(strip)+1)*2))
            self.file.write("\t\t// %s\n" % name)

            if (n==3):	# Tris
                for i in [(firstvertex+1)%n,firstvertex]:
                    self.file.write("%s\t%s\n" % (face.v[i], face.uv[i]))
                c=face.v[(firstvertex+1)%n]
                v=face.v[firstvertex]

                for face in strip:
                    for i in range(3):
                        if face.v[i]!=c and face.v[i]!=v:
                            self.file.write("%s\t%s\n" % (
                                face.v[i], face.uv[i]))
                            v=face.v[i]
                            break

            else:	# Quads
                self.file.write("%s\t%s\t%s\t%s\n" % (
                    face.v[(firstvertex+1)%n], face.uv[(firstvertex+1)%n],
                    face.v[firstvertex], face.uv[firstvertex]))
                v=face.v[(firstvertex+1)%n]
                
                for face in strip:
                    for i in range(4):
                        if face.v[i]==v:
                            self.file.write("%s\t%s\t%s\t%s\n" % (
                                face.v[(i+1)%n], face.uv[(i+1)%n],
                                face.v[(i+2)%n], face.uv[(i+2)%n]))
                            v=face.v[(i+1)%n]
                            break
                
        self.file.write("\n")
        self.nprim+=1


    #------------------------------------------------------------------------
    def updateAttr(self, hard, twoside, flat, alpha, panel):

        # Note X-Plane v7 parser requires a comment after attribute statements

        # For readability, write turn-offs before turn-ons

        # hard handled by explicit command, not attribute

        if self.twoside and not twoside:
            self.file.write("ATTR_cull\t\t//\n\n")

        if self.flat and not flat:
            self.file.write("ATTR_shade_smooth\t//\n\n")

        # alpha is implicit - doesn't appear in output file
        # panel handled by explicit command, not attribute

        # Turn Ons

        # hard handled by explicit command, not attribute

        if twoside and not self.twoside:
            self.file.write("ATTR_no_cull\t\t//\n\n")

        if flat and not self.flat:
            self.file.write("ATTR_shade_flat\t\t//\n\n")

        # alpha is implicit - doesn't appear in output file
        # panel handled by explicit command, not attribute

        self.hard=hard
        self.twoside=twoside
        self.flat=flat
        self.alpha=alpha
        self.panel=panel

    #------------------------------------------------------------------------
    def updateLayer(self, layer):
        # Layers
        if self.layermask!=1:
            if layer==1:
                self.file.write("\nATTR_LOD 0 1000\t\t// Layer 1\n\n")
            elif layer==2:
                self.file.write("\nATTR_LOD 1000 4000\t// Layer 2\n\n")
            else:
                self.file.write("\nATTR_LOD 4000 10000\t// Layer 3\n\n")

        # Reset all attributes
        self.hard=False
        self.twoside=False
        self.flat=False
        self.alpha=False
        self.panel=False
        self.layer=layer


#------------------------------------------------------------------------
if Blender.Window.EditMode():
    Blender.Draw.PupMenu("Please exit Edit Mode first.")
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
        print "ERROR:\t%s\n" % e.msg
        Blender.Draw.PupMenu("ERROR: %s" % e.msg)
        Blender.Window.DrawProgressBar(1, 'ERROR')
        if obj.file:
            obj.file.close()
