#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane Scenery (.obj)'
Blender: 232
Group: 'Export'
Tooltip: 'Export to X-Plane scenery file format (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane exporter for blender 2.34 or above
#
# Copyright (c) 2004 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web:  http://marginal.org.uk/x-planescenery/
#
# See XPlane2Blender.html for usage
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the author be held liable for any damages
# arising from the use of this software.
# 
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 
# 1. The origin of this software must not be misrepresented; you must
#    not claim that you wrote the original software. If you use this
#    software in a product, an acknowledgment in the product
#    documentation would be appreciated but is not required.
# 
# 2. Altered source versions must be plainly marked as such, and must
#    not be misrepresented as being the original software.
# 
# 3. This notice may not be removed or altered from any source
#    distribution.
#
#
# 2004-02-01 v1.00
#  - First public version
#
# 2004-02-04 v1.10
#  - Updated for Blender 2.32
#
# 2004-02-05 v1.11
#  - Removed dependency on Python installation
#
# 2004-02-08 v1.12
#  - Fixed filename bug when texture file is a png
#
# 2004-02-09 v1.13
#  - Fixed lack of comment bug on v7 objects
#
# 2004-02-29 v1.20
#  - Emulate Lines with faces
#  - Automatically generate strips where possible for faster rendering
#
# 2004-03-24 v1.30
#  - Reduced duplicate vertex limit from 0.25 to 0.1 to handle smaller objects
#  - Sort faces by type for correct rendering in X-Plane. This fixes bugs with
#    alpha and no_depth faces.
#
# 2004-04-10 v1.40
#  - Reduced duplicate vertex limit to 0.01 to handle imported objects
#  - Support 3 LOD levels: 1000,4000,10000
#
# 2004-08-22 v1.50
#  - Reversed meaning of DYNAMIC flag, since it is set by default when
#    creating new faces in Blender
#
# 2004-08-28 v1.60
#  - Added support for double-sided faces
#
# 2004-08-28 v1.61
#  - Requires Blender 234 due to changed layer semantics of Blender fix #1212
#  - Display number of X-Plane objects on import and export
#
# 2004-08-29 v1.62
#  - Light and Line colours are floats
#  - Don't generate no_depth attribute - it's broken in X-Plane 7.61
#
# 2004-08-30 v1.63
#  - Work round X-Plane 7.61 tri_fan normal bug
#
# 2004-09-02 v1.70
#

#
# X-Plane renders faces in scenery files in the order that it finds them -
# it doesn't sort by Z-buffer order or do anything intelligent at all.
# So we have to sort on export. The algorithm below isn't guaranteed to
# produce the right result in all cases, but seems to work OK in practice:
#
#  1. Output texture file name.
#  2. Output lights and lines in the order that they're found.
#     Build up global vertex list and global face list.
#  3. Output faces in the following order, joined into strips where possible.
#      - no_depth
#      - normal (usually the fullest bucket)
#      - no_depth+alpha
#      - alpha
#      (Smooth, Hard and double-sided faces are mixed up with the other
#       faces and are output in the order they're found).
#

import sys
import Blender
from Blender import NMesh, Lamp, Draw, Window

class Vertex:
    LIMIT=0.01	# max distance between vertices for them to be merged = 1/4in
    ROUND=2	# Precision, AS ABOVE
    
    def __init__(self, x, y, z, mm=0):
        self.faces=[]	# indices into face array
        if not mm:
            self.x=x
            self.y=y
            self.z=z
        else:	# apply scale, translate and swap axis
            self.x=mm[0][0]*x + mm[1][0]*y + mm[2][0]*z + mm[3][0]
            self.y=mm[0][2]*x + mm[1][2]*y + mm[2][2]*z + mm[3][2]
            self.z=-(mm[0][1]*x + mm[1][1]*y + mm[2][1]*z + mm[3][1])
            
    def __str__(self):
        return "%7.2f %7.2f %7.2f" % (self.x, self.y, self.z)
    
    def equals (self, v, fudge=LIMIT):
        if ((abs(self.x-v.x) < fudge) and
            (abs(self.y-v.y) < fudge) and
            (abs(self.z-v.z) < fudge)):
            return 1
        else:
            return 0

    def addFace(self, v):
        self.faces.append(v)

class UV:
    LIMIT=0.008	# = 1 pixel in 128, 2 pixels in 256, etc
    ROUND=4	# Precision

    def __init__(self, s, t):
        self.s=s
        self.t=t

    def __str__(self):
        return "%-6s %-6s" % (round(self.s,UV.ROUND), round(self.t,UV.ROUND))

    def equals (self, uv):
        if ((abs(self.s-uv.s) <= UV.LIMIT) and
            (abs(self.t-uv.t) <= UV.LIMIT)):
            return 1
        else:
            return 0

class Face:
    # Flags
    NO_DEPTH=1
    ALPHA=2
    DBLSIDED=4
    SMOOTH=8
    HARD=16
    BUCKET=NO_DEPTH|ALPHA

    def __init__(self, name):
        self.v=[]
        self.uv=[]
        self.flags=0
        self.name=name

    # for debug only
    def __str__(self):
        s="<"
        for v in self.v:
            s=s+("[%4.1f %4.1f %4.1f]," % (v.x, v.y, v.z))
        return s[:-1]+">"

    def addVertex(self, v):
        self.v.append(v)

    def addUV(self, uv):
        self.uv.append(uv)


#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:
    VERSION=1.70

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        self.fileformat=7  # export v6 or v7
        
        #--- class private don't touch ---
        self.filename=filename
        self.texture=""
        self.linewidth=0.1
        self.nobj=0		# Number of X-Plane objects exported

        # flags controlling export
        self.no_depth=0
        self.dblsided=0
        self.smooth=0

        # stuff for exporting faces
        self.faces=[]
        self.verts=[]

    #------------------------------------------------------------------------
    def export(self, scene):
        print "Starting OBJ export to " + self.filename
        if not self.checkFile():
            return
    
        theObjects = []
        theObjects = scene.getChildren()

        Window.DrawProgressBar(0, "Examining textures")
        self.getTexture (theObjects)
        
        self.file = open(self.filename, "w")
        self.writeHeader()
        self.writeObjects(theObjects)
        self.file.close()
        
        Window.DrawProgressBar(1, "Finished")
        print "Finished - exported %s objects\n" % self.nobj

    #------------------------------------------------------------------------
    def checkFile(self):
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
    def writeHeader(self):
        if Blender.sys.dirsep=="\\":
            systype="I"
        else:
            systype="A"
        if self.fileformat==7:
            self.file.write("%s\n700\t// \nOBJ\t// \n\n" % systype)
        else:
            self.file.write("%s\n2\t//\n\n" % systype)
        self.file.write("%s\t\t// Texture\n\n\n" % self.texture)

    #------------------------------------------------------------------------
    def getTexture (self, theObjects):
        texture=""
        erroring=0;
        nobj=len(theObjects)
        texlist=[]
        self.dolayers=0
        layers=theObjects[0].Layer
        for o in range (nobj-1,-1,-1):
            object=theObjects[o]
            
            if layers^object.Layer and not self.dolayers:
                layers=layers&object.Layer
                self.dolayers=1
                print "Info:\tMultiple Levels Of Detail found"
                
            objType=object.getType()
            if objType == "Mesh":
                mesh=object.getData()
                if mesh.hasFaceUV():
                    for face in mesh.faces:
                        if face.image:
                            if ((not texture) or
                                (str.lower(texture) ==
                                 str.lower(face.image.filename))):
                                texture = face.image.filename
                                texlist.append(str.lower(texture))
                            else:
                                if not erroring:
                                    erroring=1
                                    print "Warn:\tOBJ format supports one texture, but multiple texture files found:"
                                    print "\t\"%s\"" % texture
                                if not str.lower(face.image.filename) in texlist:
                                    texlist.append(str.lower(face.image.filename))
                                    print "\t\"%s\"" % face.image.filename
                            
        if erroring:
            print "Warn:\tSome objects will have the wrong textures"
                                    
        if not texture:
            self.texture = "none"
            return

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
            print "Warn:\tTexture must be in bmp or png format. Please convert your file."
            if self.texture[-4:-3] == ".":
                self.texture = self.texture[:-4]
        
        # try to guess correct texture path
        for prefix in ["custom object textures", "autogen textures"]:
            l=self.texture.lower().find(prefix)
            if l!=-1:
                self.texture = self.texture[l+len(prefix)+1:]
                if self.texture.find(" ")!=-1:
                    print "Warn:\tTexture file name must not contain spaces. Please fix."
                return

        print "Warn:\tCan't guess path for texture file. Please fix in the .obj file."
        l=self.texture.rfind(":")
        if l!=-1:
            self.texture = self.texture[l+1:]
        if self.texture.find(" ")!=-1:
            print "Warn:\tTexture file name must not contain spaces. Please fix."

    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):
        nobj=len(theObjects)

        if not self.dolayers:
            seq=[1]
        else:
            seq=[1,2,4]

        for layer in seq:
            self.faces=[]
            self.verts=[]
            self.updateLayer(layer)
            for o in range (nobj-1,-1,-1):
                object=theObjects[o]
                if not object.Layer&layer:
                    continue
                
                Window.DrawProgressBar(float(nobj-o)/(nobj*2),
                                       "Exporting %s%% ..." % ((nobj-o)*50/nobj))
                objType=object.getType()

                if objType == "Mesh":
                    self.sortMesh(object)
                elif objType == "Lamp":
                    self.writeLamp(object)
                elif objType == "Camera":
                    print "Info:\tIgnoring Camera \"%s\"" % object.name
                else:
                    print "Warn:\tIgnoring unsupported %s \"%s\"" % (
                        object.getType(), object.name)

            self.writeFaces()
                
            self.updateFlags(0,0,0)	# not sure if this is required
            
        if self.fileformat==7:
            self.file.write("end\t\t\t// eof\n")
        else:
            self.file.write("99\t\t\t// eof\n")
        self.file.write("\n// Built using Blender %4.2f, http://www.blender3d.org/\n// Exported using XPlane2Blender %4.2f, http://marginal.org.uk/x-planescenery/\n" % (float(Blender.Get('version'))/100, OBJexport.VERSION))

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
            c[0]=-lamp.col[0]*10,0
            c[1]=-lamp.col[1]*10,0
            c[2]=-lamp.col[2]*10,0
        else:
            c[0]=lamp.col[0]*10
            c[1]=lamp.col[1]*10
            c[2]=lamp.col[2]*10

        v=Vertex(0,0,0, object.getMatrix())
        if self.fileformat==7:
            self.file.write("light\t\t\t// %s\n" % name)
            if special:
                self.file.write("%s\t %2d     %2d     %2d\n\n" % (
                    v, c[0],c[1],c[2]))
            else:
                self.file.write("%s\t %5.2f  %5.2f  %5.2f\n\n" % (
                    v, c[0],c[1],c[2]))
        else:
            if special:
                self.file.write("1  %2d %2d %2d\t\t// %s\n" % (
                    c[0], c[1], c[2], name))
                self.file.write("1  %5.2f %5.2f %5.2f\t\t// %s\n" % (
                    c[0], c[1], c[2], name))
            self.file.write("%s\n" % v)
        self.nobj+=1


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
            c=[0.5,0,5,0,5]
    
        if self.fileformat==7:
            self.file.write("line\t\t\t// %s\n" % name)
            self.file.write("%s\t %5.2f  %5.2f  %5.2f\n" % (
                v1, c[0],c[1],c[2]))
            self.file.write("%s\t %5.2f  %5.2f  %5.2f\n\n" % (
                v2, c[0],c[1],c[2]))
        else:
            self.file.write("2  %2d %2d %2d\t\t// %s\n" % (
                c[0], c[1], c[2], name))
            self.file.write("%s\n%s\n\n" % (v1, v2))
        self.nobj+=1


    #------------------------------------------------------------------------
    def sortMesh(self, object):
        mesh=object.getData()
        mm=object.getMatrix()

        # A line is represented as a mesh with one 4-edged face, where vertices
        # at each end of the face are less than self.linewidth units apart
        if  (len(mesh.faces)==1 and
             len(mesh.faces[0].v)==4 and
             not mesh.faces[0].mode&NMesh.FaceModes.TEX):
            f=mesh.faces[0]
            v=[]
            for i in range(4):
                v.append(Vertex(f.v[i][0],f.v[i][1],f.v[i][2],mm))
            for i in range(2):
                if (v[i].equals(v[i+1],self.linewidth) and
                    v[i+2].equals(v[(i+3)%4],self.linewidth)):
                    self.writeLine(object)
                    return
            
        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(mesh.faces))

        # Build list of faces and vertices
        twoside=0
        for f in mesh.faces:
            n=len(f.v)
            if (n!=3) and (n!=4):
                print "Warn:\tIgnoring %s-edged face in mesh \"%s\"" % (
                    n, object.name)
            else:
                face=Face(object.name)
                if f.mode & NMesh.FaceModes.TILES:
                    face.flags|=Face.NO_DEPTH
                if f.transp == NMesh.FaceTranspModes.ALPHA:
                    face.flags|=Face.ALPHA
                if f.mode & NMesh.FaceModes.TWOSIDE:
                    face.flags|=Face.DBLSIDED
                    if not twoside:
                        print "Warn:\tFound two-sided face(s) in mesh \"%s\""%(
                            object.name)
                    twoside=1
                if f.smooth:
                    face.flags|=Face.SMOOTH
                if (n==4) and not (f.mode & NMesh.FaceModes.DYNAMIC):
                    face.flags|=Face.HARD
                if f.mode & NMesh.FaceModes.TEX:
                    assert len(f.uv)==n, "Missing UV in \"%s\"" % object.name

                # Remove any redundant vertices
                v=[]
                for i in range(n):
                    vertex=Vertex(f.v[i][0],f.v[i][1],f.v[i][2],mm)
                    for j in range(len(v)):
                        if vertex.equals(v[j]):
                            v[j].x=(v[j].x+vertex.x)/2
                            v[j].y=(v[j].y+vertex.y)/2
                            v[j].z=(v[j].z+vertex.z)/2
                            break
                    else:
                        v.append(vertex)
                        if f.mode & NMesh.FaceModes.TEX:
                            face.addUV(UV(f.uv[i][0],f.uv[i][1]))
                        else:	# File format requires something - using (0,0)
                            face.addUV(UV(0,0))
                if len(v)<3:
                    continue
                
                self.faces.append(face)
                for vertex in v:
                    for q in self.verts:
                        if vertex.equals(q):
                            q.x=(q.x+vertex.x)/2
                            q.y=(q.y+vertex.y)/2
                            q.z=(q.z+vertex.z)/2
                            q.addFace(len(self.faces)-1)
                            face.addVertex(q)
                            break
                    else:
                        self.verts.append(vertex)
                        vertex.addFace(len(self.faces)-1)
                        face.addVertex(vertex)
                if self.debug: print face


    #------------------------------------------------------------------------
    def writeFaces(self):

        facenum=0
        nfaces=len(self.faces)
        
        for bucket in [Face.NO_DEPTH, 0, Face.NO_DEPTH+Face.ALPHA, Face.ALPHA]:

            # Identify strips
            for faceindex in range(nfaces):
                
                if (self.faces[faceindex] and
                    (self.faces[faceindex].flags&Face.BUCKET) == bucket):
                    Window.DrawProgressBar(0.5+float(facenum)/(nfaces*2),
                                           "Exporting %s%% ..." %
                                           (50 + facenum*50/nfaces))
                    facenum=facenum+1
                    
                    startface=self.faces[faceindex]
                    strip=[startface]
                    self.faces[faceindex]=0	# take face off list
                    firstvertex=0

                    if (startface.flags & Face.HARD) and (self.fileformat==7):
                        pass	# Hard faces can't be part of a Quad_Strip
                    elif len(startface.v)==3 and (self.fileformat==7):
                        # Vertex which is member of most triangles is centre
                        tris=[]
                        for v in startface.v:
                            tri=0
                            for i in v.faces:
                                if  (self.faces[i] and
                                     len(self.faces[i].v) == 3 and
                                     (self.faces[i].flags&Face.BUCKET) == bucket):
                                    tri=tri+1
                            tris.append(tri)
                        if tris[0]>=tris[1] and tris[0]>=tris[2]:
                            c=0
                        elif tris[1]>=tris[2]:
                            c=1
                        else:
                            c=2
                        firstvertex=(c-1)%3
                        if self.debug: print "Start strip, centre=%s:\n%s" % (
                            c, startface)

                        for o in [0,2]:
                            # vertices must be in clockwise order
                            if self.debug: print "Order %s" % o
                            of=startface
                            v=(c+o)%3
                            while 1:
                                (nf,i)=self.findFace(of,v)
                                if nf>=0:
                                    of=self.faces[nf]
                                    if self.debug: print of
                                    if o==0:
                                        strip.append(of)
                                        v=(i+1)%3
                                    else:
                                        strip.insert(0, of)
                                        v=(i-1)%3
                                        firstvertex=v
                                    self.faces[nf]=0	# take face off list
                                    facenum=facenum+1
                                else:
                                    break

                    elif len(startface.v)==4:
                        # Find lowest two points
                        miny=sys.maxint
                        for i in range(4):
                            if startface.v[i].y<miny:
                                min1=i
                                miny=startface.v[i].y
                        miny=sys.maxint
                        for i in range(4):
                            if i!=min1 and startface.v[i].y<miny:
                                min2=i
                                miny=startface.v[i].y
                        # first pair contains only one of the lowest two points
                        if min2==(min1+1)%4:
                            sv=min2	#(min1-1)%4
                        else:
                            sv=min1
                        if self.debug: print "Start strip, edge=%s,%s:\n%s" % (
                            sv, (sv+1)%4, startface)

                        # Strip could maybe go two ways
                        if startface.flags&Face.SMOOTH:
                            # Vertically then Horizontally for fuselages
                            seq=[1,0]
                        else:
                            # Horizontally then Vertically
                            seq=[0,1]
                        for hv in seq:	# rotate 0 or 90
                            firstvertex=(sv+2+hv)%4
                            for o in [0,2]:
                                # vertices must be in clockwise order
                                if self.debug: print "Order %s" % (o+hv)
                                of=startface
                                v=(sv+o+hv)%4
                                while 1:
                                    (nf,i)=self.findFace(of,v)
                                    if nf>=0:
                                        of=self.faces[nf]
                                        if self.debug: print of
                                        v=(i+2)%4
                                        if o==0:
                                            strip.append(of)
                                        else:
                                            strip.insert(0, of)
                                            firstvertex=v
                                        self.faces[nf]=0  # take face off list
                                        facenum=facenum+1
                                    else:
                                        break
                            # not both horiontally and vertically
                            if len(strip)>1:
                                break

                    if len(strip)>1:
                        if len(startface.v)==3:
                            striptype="Tri"
                        else:
                            striptype="Quad"
                        print "Info:\tFound strip of %s %ss in Mesh \"%s\"" % (
                            len(strip), striptype, startface.name)
                    self.writeStrip(strip,firstvertex)
                

    #------------------------------------------------------------------------
    # Return index of a face which has the same number of edges, same flags,
    # has v and v+1 as vertices and faces the same way as the supplied face.
    def findFace (self,face,v):
        n=len(face.v)
        v1=face.v[v]
        v2=face.v[(v+1)%n]
        uv1=face.uv[v]
        uv2=face.uv[(v+1)%n]
        for faceindex in v1.faces:
            f=self.faces[faceindex]
            if f and f.flags==face.flags and len(f.v)==n:
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
    # Assumes that any "hard" faces are in a strip of length 1
    def writeStrip (self,strip,firstvertex):
        
        face=strip[0]
        n=len(face.v)
        self.updateFlags(face.flags&Face.NO_DEPTH, face.flags&Face.DBLSIDED,
                         face.flags&Face.SMOOTH)
        
        if (len(strip))==1:            
            # When viewing the visible side of a face
            #  - Blender stores vertices anticlockwise
            #  - XPlane expects clockwise, starting with top right
            # So find top right vertex, then write in reverse order
            maxX=maxY=-1
            for i in range(n):
                if (maxX<face.uv[i].s):
                    maxX=face.uv[i].s
                if (maxY<face.uv[i].t):
                    maxY=face.uv[i].t
                if (maxX==face.uv[i].s) and (maxY==face.uv[i].t):
                    topright=i
                            
            if self.fileformat==7:
                if (n==3):
                    self.file.write ("tri\t")
                elif (face.flags & Face.HARD):
                    self.file.write ("quad_hard")
                else:
                    self.file.write ("quad\t")
                self.file.write("\t\t// %s\n" % face.name)
            else:
                if (n==4) and (face.flags & Face.HARD):
                    poly=5	# make quad "hard"
                else:
                    poly=n
                self.file.write("%s  %-6s %-6s %-6s %-6s" % (
                    poly,
                    round(face.uv[(topright-2)%n].s,UV.ROUND),
                    round(face.uv[ topright     ].s,UV.ROUND),
                    round(face.uv[(topright-2)%n].t,UV.ROUND),
                    round(face.uv[ topright     ].t,UV.ROUND)))
                self.file.write("\t// %s\n" % face.name)

            for i in range(topright, topright-n, -1):
                if self.fileformat==7:
                    self.file.write("%s\t  %s\n" % (face.v[i%n], face.uv[i%n]))
                else:
                    self.file.write("%s\n" % face.v[i%n])

        else:	# len(strip)>1
            if self.debug:
                for f in strip:
                    print f

            # Work round bug in X-Plane 7.61 where one tri is rendered
            # incorrectly (wrong normal?) under some situations.
            # Bug appears reliably to be avoided if the tri_fan is regular,
            # but that's hard to work out. So assume it is regular if it is
            # closed. Split back into tris unless it is closed.
            if n==3 and len(strip)>1:
                # tri_fan is closed if first and last faces share two vertices
                common=0
                for i in range(3):
                    for j in range(3):
                        if strip[0].v[i].equals(strip[-1].v[j]):
                            common+=1
                if len(strip)==2 or common<2:
                    while len(strip):
                        self.writeStrip ([strip.pop()], 0)
                    return;
                
            if self.fileformat==7:
                if n==3:
                    self.file.write ("tri_fan %s" % (len(strip)+2))
                else:
                    self.file.write ("quad_strip %s" % ((len(strip)+1)*2))
            else:
                self.file.write ("%s\t" % -(len(strip)+1))
            self.file.write("\t\t// %s\n" % face.name)

            if (n==3):	# Tris
                for i in [(firstvertex+1)%n,firstvertex]:
                    self.file.write("%s\t  %s\n" % (face.v[i], face.uv[i]))
                c=face.v[(firstvertex+1)%n]
                v=face.v[firstvertex]

                for face in strip:
                    for i in range(3):
                        if face.v[i]!=c and face.v[i]!=v:
                            self.file.write("%s\t  %s\n" % (
                                face.v[i], face.uv[i]))
                            v=face.v[i]
                            break

            else:	# Quads
                if self.fileformat==7:
                    self.file.write("%s\t  %s\t%s\t  %s\n" % (
                        face.v[(firstvertex+1)%n], face.uv[(firstvertex+1)%n],
                        face.v[firstvertex], face.uv[firstvertex]))
                else:
                    self.file.write("%s\t%s\t  %-6s %-6s %-6s %-6s\n" % (
                        face.v[(firstvertex+1)%n], face.v[firstvertex],
                        round(face.uv[(firstvertex+1)%n].s,UV.ROUND),
                        round(face.uv[ firstvertex     ].s,UV.ROUND),
                        round(face.uv[(firstvertex+1)%n].t,UV.ROUND),
                        round(face.uv[ firstvertex     ].t,UV.ROUND)))
                v=face.v[(firstvertex+1)%n]
                
                for face in strip:
                    for i in range(4):
                        if face.v[i]==v:
                            if self.fileformat==7:
                                self.file.write("%s\t  %s\t%s\t  %s\n" % (
                                    face.v[(i+1)%n], face.uv[(i+1)%n],
                                    face.v[(i+2)%n],  face.uv[(i+2)%n]))
                            else:
                                self.file.write("%s\t%s\t  %-6s %-6s %-6s %-6s\n" % (
                                    face.v[(i+1)%n], face.v[(i+2)%n],
                                    round(face.uv[(i+1)%n].s,UV.ROUND),
                                    round(face.uv[(i+2)%n].s,UV.ROUND),
                                    round(face.uv[(i+1)%n].t,UV.ROUND),
                                    round(face.uv[(i+2)%n].t,UV.ROUND)))
                                
                            v=face.v[(i+1)%n]
                            break
                
        self.file.write("\n")
        self.nobj+=1

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
    def updateFlags(self, no_depth, dblsided, smooth):
        if not self.fileformat==7:
            return	# v6 format doesn't support this stuff

        # For readability, write turn-offs before turn-ons
        # Note X-Plane parser requires a comment after attribute statements

# Grrrr, no_depth is broken in X-Plane 7.61
#       if self.no_depth and not no_depth:
#           self.file.write("ATTR_depth\t\t//\n\n")
        if self.dblsided and not dblsided:
            self.file.write("ATTR_cull\t\t//\n\n")
        if self.smooth and not smooth:
            self.file.write("ATTR_shade_flat\t\t//\n\n")
            
#       if no_depth and not self.no_depth:
#           self.file.write("ATTR_no_depth\t\t//\n\n")
        if dblsided and not self.dblsided:
            self.file.write("ATTR_no_cull\t\t//\n\n")
        if smooth and not self.smooth:
            self.file.write("ATTR_shade_smooth\t//\n\n")
                
        self.no_depth=no_depth
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
    obj.export(scene)
