#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane v7 Scenery (.obj)'
Blender: 232
Group: 'Export'
Tooltip: 'Export to X-Plane v7 scenery file format (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane exporter for blender 2.34 or above
#
# Copyright (c) 2004 Jonathan Harris
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
#  - Panel ploygons must go last in file.
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
#  - Work round X-Plane 8.00-8.03 limitation where quad_cockpit polys must
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

#
# X-Plane renders polygons in scenery files mostly in the order that it finds
# them - it detects use of alpha and deletes wholly transparent polys, but
# doesn't sort by Z-buffer order.
#
# Panel polygons must come last (at least in v8.00-8.04) for LIT textures to
# work for non-panel ploygons. The last polygon in the file must not be a
# quad_cockpit with texture outside 1024x768 else everything goes wierd.
#
# So we have to sort on export. The algorithm below isn't guaranteed to
# produce the right result in all cases, but seems to work OK in practice:
#
#  1. Output header and texture file name.
#  2. For each layer:
#     3. Output lights and lines in the order that they're found.
#        Build up global vertex list and global face list.
#     4. Output mesh faces in the following order, in strips where possible:
#        - normal (usually the fullest bucket)
#        - alpha
#        - panel (with or without alpha)
#        (Smooth, Hard and Two-sided faces are mixed up with the other faces
#        and are output in the order they're found).
#

import sys
import Blender
from Blender import NMesh, Lamp, Draw, Window
from math import sqrt
#import time

class ExportError(Exception):
    def __init__(self, msg):
        self.msg = msg

class Vertex:
    LIMIT=0.001	# max distance between vertices for them to be merged = 1/4in
    ROUND=3	# Precision, AS ABOVE
    
    def __init__ (self, x, y, z, mm=0):
        self.faces=[]	# indices into face array
        if not mm:
            self.x=x
            self.y=y
            self.z=z
        else:	# apply scale, translate and swap axis
            self.x=mm[0][0]*x + mm[1][0]*y + mm[2][0]*z + mm[3][0]
            self.y=mm[0][2]*x + mm[1][2]*y + mm[2][2]*z + mm[3][2]
            self.z=-(mm[0][1]*x + mm[1][1]*y + mm[2][1]*z + mm[3][1])
            
    def __str__ (self):
        return "%7.3f %7.3f %7.3f" % (
            round(self.x, Vertex.ROUND),
            round(self.y, Vertex.ROUND),
            round(self.z, Vertex.ROUND))
    
    def __add__ (self, other):
        return Vertex(self.x+other.x, self.y+other.y, self.z+other.z)
        
    def __sub__ (self, other):
        return Vertex(self.x-other.x, self.y-other.y, self.z-other.z)
        
    def equals (self, v, fudge=LIMIT):
        if ((abs(self.x-v.x) < fudge) and
            (abs(self.y-v.y) < fudge) and
            (abs(self.z-v.z) < fudge)):
            return 1
        else:
            return 0

    def norm (self):
        hyp=sqrt(self.x*self.x + self.y*self.y + self.z*self.z)
        return Vertex(self.x/hyp, self.y/hyp, self.z/hyp)

    def addFace (self, v):
        self.faces.append(v)

class UV:
    LIMIT=0.008	# = 1 pixel in 128, 2 pixels in 256, etc
    ROUND=4	# Precision

    def __init__ (self, s, t):
        self.s=s
        self.t=t

    def __str__ (self):
        return "%-6s %-6s" % (round(self.s,UV.ROUND), round(self.t,UV.ROUND))

    def equals (self, uv):
        if ((abs(self.s-uv.s) <= UV.LIMIT) and
            (abs(self.t-uv.t) <= UV.LIMIT)):
            return 1
        else:
            return 0

class Face:
    # Flags
    TILES=1
    ALPHA=2
    DBLSIDED=4
    SMOOTH=8
    HARD=16
    PANEL=32
    BUCKET=ALPHA|PANEL

    def __init__ (self, name):
        self.v=[]
        self.uv=[]
        self.flags=0
        self.name=name

    # for debug only
    def __str__ (self):
        s="<"
        for v in self.v:
            s=s+("[%s]" % v)
        return s+">"

    def addVertex (self, v):
        self.v.append(v)

    def addUV (self, uv):
        self.uv.append(uv)


#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:
    VERSION=1.90

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        self.strips=1	# whether to make strips
        
        #--- class private don't touch ---
        self.file=0
        self.filename=filename
        self.dolayers=0
        self.iscockpit=((filename.lower().find("_cockpit.obj") != -1) or
                        (filename.lower().find("_cockpit_inn.obj") != -1) or
                        (filename.lower().find("_cockpit_out.obj") != -1))
        self.havepanel=0
        self.texture=""
        self.linewidth=0.1
        self.nprim=0		# Number of X-Plane primitives exported

        # flags controlling export
        self.tiles=0
        self.dblsided=0
        self.smooth=-1		# >=7.30 defaults to smoothed, but be explicit

    #------------------------------------------------------------------------
    def export(self, scene):
        theObjects = []
        theObjects = scene.getChildren()

        print "Starting OBJ export to " + self.filename
        self.getTexture (theObjects)
        
        if not self.checkFile():
            return

        #clock=time.clock()	# Processor time
        Blender.Window.WaitCursor(1)
        Window.DrawProgressBar(0, "Examining textures")

        self.file = open(self.filename, "w")
        self.writeHeader ()
        self.writeObjects (theObjects)
        self.checkLayers (theObjects)
        self.file.close ()
        
        Window.DrawProgressBar(1, "Finished")
        print "Finished - exported %s primitives\n" % self.nprim
        #print "%s CPU time\n" % (time.clock()-clock)

    #------------------------------------------------------------------------
    def checkFile (self):
        try:
            file = open(self.filename, "rb")
        except IOError:
            return 1        
        file.close()
        if Draw.PupMenu("Overwrite?%%t|Overwrite file: %s" % self.filename)!=1:
            print "Cancelled\n"
            return 0
        return 1

    #------------------------------------------------------------------------
    def checkLayers (self, theObjects):
        for object in theObjects:
            if not object.Layer & 7:
                break
        else:
            return
        print "Warn:\tObjects were found outside layers 1-3 and were not exported"

    #------------------------------------------------------------------------
    def writeHeader (self):
        if Blender.sys.progname.find("blender.app")!=-1:
            systype='A'
        else:
            systype='I'
        self.file.write("%s\n700\t// \nOBJ\t// \n\n" % systype)
        self.file.write("%s\t\t// Texture\n\n" % self.texture)
        if not self.iscockpit:
            self.file.write("ATTR_poly_os 0\t\t//\n\n")

    #------------------------------------------------------------------------
    def getTexture (self, theObjects):
        texture=""
        multierr=0
        panelerr=0
        nobj=len(theObjects)
        texlist=[]
        layers=0

        for o in range (nobj-1,-1,-1):
            object=theObjects[o]

            if not self.iscockpit:
                if layers==0:
                    layers = object.Layer&7
                elif (object.Layer&7 and layers^(object.Layer&7) and
                      not self.dolayers):
                    self.dolayers=1
                    print "Info:\tMultiple Levels Of Detail found"
                
            objType=object.getType()
            if objType == "Mesh" and (object.Layer & 7):
                mesh=object.getData()
                if mesh.hasFaceUV():
                    for face in mesh.faces:
                        if face.image:
                            if face.image.name.lower().find("panel.")!=-1:
                                # Check that at least one panel texture is OK
                                if not self.havepanel:
                                    self.havepanel=1
                                    self.iscockpit=1
                                    self.dolayers=0
                                    panelerr=1
                                if panelerr and object.Layer&1:
                                    for uv in face.uv:
                                        if (uv[0]<0.0  or uv[0]>1.0 or
                                            uv[1]<0.25 or uv[1]>1.0):
                                            break
                                    else:
                                        panelerr=0
                            else:
                                if ((not texture) or
                                    (str.lower(texture) ==
                                     str.lower(face.image.filename))):
                                    texture = face.image.filename
                                    texlist.append(str.lower(texture))
                                else:
                                    if not multierr:
                                        multierr=1
                                        print "Warn:\tMultiple texture files found:"
                                        print "\t\"%s\"" % texture
                                    if not str.lower(face.image.filename) in texlist:
                                        texlist.append(str.lower(face.image.filename))
                                        print "\t\"%s\"" % face.image.filename
            elif (self.iscockpit and (object.Layer & 7) and objType == "Lamp"
                  and object.getData().getType() == Lamp.Types.Lamp):
                raise ExportError("Cockpit objects can't contain lights.")
                            
        if multierr:
            raise ExportError("OBJ format supports one texture, but multiple texture files found.")
                                    
        if panelerr:
            raise ExportError("At least one instrument panel texture must be within 1024x768.")

        if not texture:
            self.texture = "none"
            return

        l=texture.rfind(Blender.sys.dirsep)
        if l!=-1:
            l=l+1
        else:
            l=0
        if texture[l:].find(" ")!=-1:
            raise ExportError("Texture filename \"%s\" contains spaces.\n\tPlease rename the file. Use Image->Replace to load the renamed file." % texture[l:])

        self.texture=""
        for i in range(len(texture)):
            if texture[i]==Blender.sys.dirsep:
                self.texture+=":"
            else:
                self.texture+=texture[i]

        if self.texture[-4:].lower() == ".bmp":
            self.texture = self.texture[:-4]
        elif self.texture[-4:].lower() == ".png":
            self.texture = self.texture[:-4]
        else:
            raise ExportError("Texture must be in bmp or png format.\n\tPlease convert the file. Use Image->Replace to load the new file.")
        
        # try to guess correct texture path
        if not self.iscockpit:
            for prefix in ["custom object textures", "autogen textures"]:
                l=self.texture.lower().find(prefix)
                if l!=-1:
                    self.texture = self.texture[l+len(prefix)+1:]
                    return
            print "Warn:\tCan't guess path for texture file. Please fix in the .obj file."

        l=self.texture.rfind(":")
        if l!=-1:
            self.texture = self.texture[l+1:]

    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):

        if not self.dolayers:
            seq=[1]
        else:
            seq=[1,2,4]

        # Count the objects
        nobj=0
        objlen=1
        for layer in seq:
            for object in theObjects:
                if object.Layer&layer:
                    objlen=objlen+1
        objlen=objlen*4	# 4 passes

        for layer in seq:
            self.updateLayer(layer)
            faces=[]	# Per-mesh list of list of faces
            verts=[]	# Per-mesh list of list of vertices

            # Four passes
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
                face=0
                vert=0
                if objType == "Mesh":
                    (face,vert)=self.sortMesh(object)
                elif objType == "Lamp":
                    self.writeLamp(object)
                elif objType == "Camera":
                    print "Info:\tIgnoring Camera \"%s\"" % object.name
                else:
                    print "Warn:\tIgnoring unsupported %s \"%s\"" % (
                        object.getType(), object.name)
                faces.append(face)
                verts.append(vert)

            # Hack! Find a kosher panel texture and put it last
            if self.havepanel:
                panelsorted=0
                i=0
                while not panelsorted:
                    if not faces[i]:
                        continue

                    for j in range(len(faces[i])):
                        if faces[i][j].flags&Face.PANEL:
                            for uv in faces[i][j].uv:
                                if (uv.s<0.0  or uv.s>1.0 or
                                    uv.t<0.25 or uv.t>1.0):
                                    break
                            else:
                                faces.append([faces[i][j]])
                                verts.append([0])	# Not used for panels
                                faces[i][j]=0		# Remove original face
                                panelsorted=1
                                break
                    i=i+1

            # 2nd-4th pass: Output meshes
            for bucket in [0, Face.ALPHA, Face.ALPHA+Face.PANEL]:
                for i in range(len(faces)):
                    Window.DrawProgressBar(float(nobj)/objlen,
                                           "Exporting %s%% ..." % (
                        nobj*100/objlen))
                    nobj=nobj+1

                    if faces[i]:
                        self.writeFaces(faces[i], verts[i], bucket)
                
            self.updateFlags(0,0,0)	# not sure if this is required
            
        self.file.write("end\t\t\t// eof\n\n")
        self.file.write("// Built using Blender %4.2f, http://www.blender3d.org/\n// Exported using XPlane2Blender %4.2f, http://marginal.org.uk/x-planescenery/\n" % (float(Blender.Get('version'))/100, self.VERSION))

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
            v.append(Vertex(face.v[i][0],face.v[i][1],face.v[i][2],mm))
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
    def sortMesh(self, object):
        mesh=object.getData()
        mm=object.getMatrix()

        # A line is represented as a mesh with one 4-edged face, where vertices
        # at each end of the face are less than self.linewidth units apart
        if (len(mesh.faces)==1 and len(mesh.faces[0].v)==4 and
            not mesh.faces[0].mode&NMesh.FaceModes.TEX):
            f=mesh.faces[0]
            v=[]
            for i in range(4):
                v.append(Vertex(f.v[i][0],f.v[i][1],f.v[i][2],mm))
            for i in range(2):
                if (v[i].equals(v[i+1],self.linewidth) and
                    v[i+2].equals(v[(i+3)%4],self.linewidth)):
                    self.writeLine(object)
                    return (0,0)	# Not a mesh any more
            
        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(mesh.faces))

        # Build list of faces and vertices
        twosideerr=0
        faces=[]
        verts=[]
        for f in mesh.faces:
            n=len(f.v)
            if not n in [3,4]:
                print "Warn:\tIgnoring %s-edged face in mesh \"%s\"" % (
                    n, object.name)
            else:
                face=Face(object.name)
                #if f.mode & NMesh.FaceModes.TILES:
                #    face.flags|=Face.TILES
                if f.transp == NMesh.FaceTranspModes.ALPHA:
                    face.flags|=Face.ALPHA
                if f.mode & NMesh.FaceModes.TWOSIDE:
                    face.flags|=Face.DBLSIDED
                    if not twosideerr:
                        print "Warn:\tFound two-sided face(s) in mesh \"%s\""%(
                            object.name)
                    twosideerr=1
                if f.smooth:
                    face.flags|=Face.SMOOTH
                if (n==4) and f.image and f.image.name.lower().find("panel.")!=-1:
                    # Sort is easier if we also assume alpha
                    face.flags|=(Face.PANEL|Face.ALPHA)
                elif (n==4) and not (f.mode & NMesh.FaceModes.DYNAMIC):
                    face.flags|=Face.HARD
                if f.mode & NMesh.FaceModes.TEX:
                    assert len(f.uv)==n, "Missing UV in \"%s\"" % object.name

                v=[]
                for i in range(n):
                    vertex=Vertex(f.v[i][0],f.v[i][1],f.v[i][2],mm)
                    for q in verts:
                        if vertex.equals(q):
                            q.x = (q.x + vertex.x) / 2
                            q.y = (q.y + vertex.y) / 2
                            q.z = (q.z + vertex.z) / 2
                            face.addVertex(q)
                            break
                    else:
                        verts.append(vertex)
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
                    print "Warn:\tIgnoring degenerate face in mesh \"%s\"" % (
                        object.name)
                    continue

                # Add this face to the list and add pointers from the vertices
                faces.append(face)
                for vertex in face.v:
                    vertex.addFace(len(faces)-1)
                
                if self.debug: print face

        return (faces,verts)

    #------------------------------------------------------------------------
    def writeFaces(self, faces, verts, bucket):

        # Identify strips
        for faceindex in range(len(faces)):
                
            if (faces[faceindex] and
                (faces[faceindex].flags&Face.BUCKET) == bucket):

                startface=faces[faceindex]
                strip=[startface]
                faces[faceindex]=0	# take face off list
                firstvertex=0
                        
                if (not self.strips or
                    startface.flags & Face.HARD or
                    startface.flags & Face.PANEL):
                    # Can't be part of a Quad_Strip
                    self.writeStrip(strip,0)

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
                        if common==2 or startface.flags&Face.SMOOTH:
                            print "Info:\tFound  Tri_Fan   of %2d faces in Mesh \"%s\"" % (len(strip), startface.name)
                            self.writeStrip(strip,firstvertex)
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
                    
                    if len(strip)>1:
                        print "Info:\tFound  Tri_Strip of %2d faces in Mesh \"%s\"" % (len(strip), startface.name)
                    
                    self.writeStrip(strip,firstvertex)
                    
                elif len(startface.v)==4:
                    # Find most horizontal edge
                    miny=sys.maxint
                    for i in range(4):
                        q=(startface.v[i]-startface.v[(i+1)%4]).norm()
                        if abs(q.y)<miny:
                            sv=i
                            miny=abs(q.y)
                    
                    if self.debug: print "Start strip, edge=%s,%s:\n%s" % (
                        sv, (sv+1)%4, startface)

                    # Strip could maybe go two ways
                    if startface.flags&Face.SMOOTH:
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

                    if len(strip)>1:
                        print "Info:\tFound Quad_Strip of %2d faces in Mesh \"%s\"" % (len(strip), startface.name)
                    self.writeStrip(strip,firstvertex)
                

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
    def writeStrip (self,strip,firstvertex):
        
        face=strip[0]
        n=len(face.v)
        self.updateFlags(face.flags&Face.TILES, face.flags&Face.DBLSIDED,
                         face.flags&Face.SMOOTH)
        
        if (len(strip))==1:            
            # Oh for fuck's sake, X-Plane 8.00-8.04 loses the plot unless
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
            elif (face.flags & Face.HARD):
                self.file.write ("quad_hard")
            else:
                self.file.write ("quad\t")
            self.file.write("\t\t// %s\n" % face.name)

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
            self.file.write("\t\t// %s\n" % face.name)

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
    def updateLayer(self,layer):
        if not self.dolayers:
            return
        if layer==1:
            self.file.write("\nATTR_LOD 0 1000\t\t// Layer 1\n\n")
        elif layer==2:
            self.file.write("\nATTR_LOD 1000 4000\t// Layer 2\n\n")
        else:
            self.file.write("\nATTR_LOD 4000 10000\t// Layer 3\n\n")


    #------------------------------------------------------------------------
    def updateFlags(self, tiles, dblsided, smooth):

        # For readability, write turn-offs before turn-ons
        # Note X-Plane parser requires a comment after attribute statements

        # Grrrr, no_depth is broken from X-Plane 7.61
        #if self.tiles and not tiles:
        #    self.file.write("ATTR_depth\t\t//\n\n")
        if self.dblsided and not dblsided:
            self.file.write("ATTR_cull\t\t//\n\n")
        if self.smooth and not smooth:
            self.file.write("ATTR_shade_flat\t\t//\n\n")
            
        #if tiles and not self.tiles:
        #    self.file.write("ATTR_no_depth\t\t//\n\n")
        if dblsided and self.dblsided<=0:
            self.file.write("ATTR_no_cull\t\t//\n\n")
        if smooth and self.smooth<=0:
            self.file.write("ATTR_shade_smooth\t//\n\n")
                
        self.tiles=tiles
        self.dblsided=dblsided
        self.smooth=smooth

    
#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

if Blender.Get('version') < 234:
    Blender.Draw.PupMenu("ERROR:\tRequires Blender version 2.34 or later.")
elif Blender.Window.EditMode():
    Blender.Draw.PupMenu("Please exit Edit Mode first.")
else:
    baseFileName=Blender.Get('filename')
    if baseFileName.find('.') != -1:
        dots=Blender.Get('filename').split('.')[0:-1]
    else:
        dots=[baseFileName]

    dots+=["obj"]
    objFile=".".join(dots)

    obj=OBJexport(objFile)
    scene = Blender.Scene.getCurrent()
    try:
        obj.export(scene)
    except ExportError, e:
        Window.DrawProgressBar(1, "Error")
        msg="ERROR:\t"+e.msg+"\n"
        print msg
        Blender.Draw.PupMenu(msg)
        if obj.file:
            obj.file.close()
