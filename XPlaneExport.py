#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane'
Blender: 230
Group: 'Export'
Tooltip: 'Export to X-Plane file format (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane exporter for blender 2.32 or above, version 1.20
#
# Copyright (c) 2004 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web: http://marginal.org.uk/x-planescenery/
#
# See XPlaneReadme.txt for usage
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
# 2004-02-01 v1.00 by Jonathan Harris <x-plane@marginal.org.uk>
#  - First public version
#
# 2004-02-04 v1.10 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Updated for Blender 2.32
#
# 2004-02-05 v1.11 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Removed dependency on Python installation
#  - Import at cursor, not origin
#
# 2004-02-08 v1.12 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Export: Fixed filename bug when texture file is a png
#  - Import: Fixed refusing to recognise DOS-mode v6 files
#  - Import: Fixed triangle texture rotation with v6 files
#
# 2004-02-09 v1.13 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Import: Fixed filename bug when texture file is a png
#  - Export: Fixed lack of comment bug on v7 objects
#
# 2004-02-29 v1.20 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Emulate Lines with faces
#  - Import: Join adjacent faces into meshes for easier and fast editing
#  - Export: Automatically generate strips where possible for faster rendering
#

import sys
import Blender
from Blender import NMesh, Lamp, Draw, Window

class Vertex:
    LIMIT=0.25	# max distance between vertices for them to be merged =3 inches
    ROUND=1	# Precision =about an inch
    
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
        return "%7.1f %7.1f %7.1f" % (self.x, self.y, self.z)
    
    def equals (self, v):
        if ((abs(self.x-v.x) <= Vertex.LIMIT) and
            (abs(self.y-v.y) <= Vertex.LIMIT) and
            (abs(self.z-v.z) <= Vertex.LIMIT)):
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
    HARD=1    
    NO_DEPTH=2
    SMOOTH=4

    def __init__(self):
        self.v=[]
        self.uv=[]
        self.flags=0

    # for debug only
    def __str__(self):
        s="<"
        for v in self.v:
            s=s+("[%3d %3d %3d]," % (v.x, v.y, v.z))
        return s[:-1]+">"

    def addVertex(self, v):
        self.v.append(v)

    def addUV(self, uv):
        self.uv.append(uv)


#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:
    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.debug=0	# extra debug info in console
        self.fileformat=7  # export v6 or v7
        
        #--- class private don't touch ---
        self.filename=filename
        self.texture=""

        # random stuff
        if sys.platform=="win32":
            self.dirsep="\\"
        else:
            self.dirsep="/"

        # flags controlling export
        self.smooth=0
        self.no_depth=0

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
        print "Finished\n"

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
        banner="Exported from blender3d using XPlane2Blender - http://marginal.org.uk/x-planescenery/"
        if self.fileformat==7:
            self.file.write("I\n700\t// %s\nOBJ\n\n" % banner)
        else:
            self.file.write("I\n2\t// %s\n\n" % banner)
        self.file.write("%s\t\t// Texture\n\n\n" % self.texture)

    #------------------------------------------------------------------------
    def getTexture (self, theObjects):
        texture=""
        erroring=0;
        nobj=len(theObjects)
        texlist=[]
        for o in range (nobj-1,-1,-1):
            object=theObjects[o]
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
            if texture[i]==self.dirsep:
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
                return

        print "Warn:\tCan't guess path for texture file. Please fix in the .obj file."
        l=self.texture.rfind(":")
        if l!=-1:
            self.texture = self.texture[l+1:]

    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):
        nobj=len(theObjects)
        for o in range (nobj-1,-1,-1):
            Window.DrawProgressBar(float(nobj-o)/nobj,
                                   "Exporting %s%% ..." % ((nobj-o)*100/nobj))
            object=theObjects[o]
            objType=object.getType()

            if objType == "Mesh":
                self.writeMesh(object)
            elif objType == "Lamp":
                self.writeLamp(object)
            elif objType == "Camera":
                print "Info:\tIgnoring Camera \"%s\"" % object.name
            else:
                print "Warn:\tIgnoring unsupported %s \"%s\"" % (
                    object.getType(), object.name)

        self.updateFlags(0,0)	# not sure if this is required
        if self.fileformat==7:
            self.file.write("end\t\t\t// eof\n")
        else:
            self.file.write("99\t\t\t// eof\n")

    #------------------------------------------------------------------------
    def writeLamp(self, object):
        lamp=object.getData()
        name=lamp.getName()
        
        if lamp.getType() != Lamp.Types.Lamp:
            print "Info:\tIgnoring Area, Spot, Sun or Hemi lamp \"%s\"" % name
            return
        
        if self.verbose:
            print "Info:\tExporting Light \"%s\"" % name

        lname=name.lower()
        c=[0,0,0]
        if not lname.find("pulse"):
            c[0]=c[1]=c[2]=99
        elif not lname.find("strobe"):
            c[0]=c[1]=c[2]=98
        elif not lname.find("traffic"):
            c[0]=c[1]=c[2]=97
        elif not lname.find("flash"):
            c[0]=-int(round(lamp.col[0]*10,0))
            c[1]=-int(round(lamp.col[1]*10,0))
            c[2]=-int(round(lamp.col[2]*10,0))
        else:
            c[0]=int(round(lamp.col[0]*10,0))
            c[1]=int(round(lamp.col[1]*10,0))
            c[2]=int(round(lamp.col[2]*10,0))
                    
        v=Vertex(0,0,0, object.getMatrix())
        if self.fileformat==7:
            self.file.write("light\t\t\t// Light: %s\n" % name)
            self.file.write("%s\t  %3d %3d %3d\n\n\n" % (v, c[0],c[1],c[2]))
        else:
            self.file.write("1  %3d %3d %3d\t\t// Light: %s\n" % (
                c[0], c[1], c[2], name))
            self.file.write("%s\n\n" % v)
            
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
        if v[0].equals(v[1]) and v[2].equals(v[3]):
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
            c=[int(round(mesh.materials[face.mat].R*10,0)),
               int(round(mesh.materials[face.mat].G*10,0)),
               int(round(mesh.materials[face.mat].B*10,0))]
        else:
            c=[0.5,0,5,0,5]
    
        if self.fileformat==7:
            self.file.write("line\t\t\t// Line: %s\n" % name)
            self.file.write("%s\t  %3d %3d %3d\n" % (v1, c[0],c[1],c[2]))
            self.file.write("%s\t  %3d %3d %3d\n\n\n" % (v2, c[0],c[1],c[2]))
        else:
            self.file.write("2  %3d %3d %3d\t\t// Line: %s\n" % (
                c[0], c[1], c[2], name))
            self.file.write("%s\n%s\n\n\n" % (v1, v2))


    #------------------------------------------------------------------------
    def writeMesh(self, object):
        mesh=object.getData()
        mm=object.getMatrix()
        name=object.name

        # A line is represented as a mesh with one 4-edged face, where vertices
        # at each end of the face/line are less than Vertex.LIMIT units apart
        if  (len(mesh.faces)==1 and
             len(mesh.faces[0].v)==4 and
             not mesh.faces[0].mode&NMesh.FaceModes.TEX):
            f=mesh.faces[0]
            v=[]
            for i in range(4):
                v.append(Vertex(f.v[i][0],f.v[i][1],f.v[i][2],mm))
            for i in range(2):
                if v[i].equals(v[i+1]) and v[i+2].equals(v[(i+3)%4]):
                    self.writeLine(object)
                    return
            
        if self.verbose:
            print "Info:\tExporting Mesh \"%s\"" % object.name
        if self.debug:
            print "Mesh \"%s\" %s faces" % (object.name, len(mesh.faces))

        # Build list of faces and vertices
        faces=[]
        verts=[]
        for f in mesh.faces:
            n=len(f.v)
            if (n!=3) and (n!=4):
                print "Warn:\tIgnoring %s-edged face in mesh \"%s\"" % (
                    n, object.name)
            else:
                if (f.mode & NMesh.FaceModes.TWOSIDE):
                    print "Warn:\tMesh \"%s\" has double-sided face" % (
                        object.name)
                face=Face()
                if f.smooth:
                    face.flags|=Face.SMOOTH
                if (n==4) and (f.mode & NMesh.FaceModes.DYNAMIC):
                    face.flags|=Face.HARD
                if f.mode & NMesh.FaceModes.TILES:
                    face.flags|=Face.NO_DEPTH
                if f.mode & NMesh.FaceModes.TEX:
                    for uv in f.uv:
                        face.addUV(UV(uv[0],uv[1]))
                    assert len(face.uv)==n, "Missing UV in \"%s\""%object.name
                else:
                    # File format requires something - using (0,0)
                    for i in range(n):
                        face.addUV(UV(0,0))

                # "hard" faces can't be part of a Quad_Strip so just write now.
                # Also, for simplicity, write out no_depth faces individually.
                if  ((face.flags & (Face.HARD|Face.NO_DEPTH)) or
                     ((n==3) and not (self.fileformat==7))):
                    for nmv in f.v:
                        vertex=Vertex(nmv.co[0],nmv.co[1],nmv.co[2],mm)
                        vertex.addFace(0)
                        face.addVertex(vertex)
                    self.writeStrip([face],0,name)
                    name=0
                else:
                    faces.append(face)
                    for nmv in f.v:
                        vertex=Vertex(nmv.co[0],nmv.co[1],nmv.co[2],mm)
                        for v in verts:
                            if vertex.equals(v):
                                v.x=(v.x+vertex.x)/2
                                v.y=(v.y+vertex.y)/2
                                v.z=(v.z+vertex.z)/2
                                v.addFace(len(faces)-1)
                                face.addVertex(v)
                                break
                        else:
                            verts.append(vertex)
                            vertex.addFace(len(faces)-1)
                            face.addVertex(vertex)
                    if self.debug: print face

        # Identify strips
        for faceindex in range(len(faces)):
            if faces[faceindex]:
                startface=faces[faceindex]
                strip=[startface]
                faces[faceindex]=0	# take face off list
                firstvertex=0
                
                if len(startface.v)==3:	# Tris
                    # Use vertex which is member of most triangles as centre
                    striptype="Tri"
                    tris=[]
                    for v in startface.v:
                        tri=0
                        for i in v.faces:
                            if faces[i] and (len(faces[i].v)==3): tri=tri+1
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
                            (nf,i)=self.findFace(faces,of,v)
                            if nf>=0:
                                of=faces[nf]
                                if self.debug: print of
                                if o==0:
                                    strip.append(of)
                                    v=(i+1)%3
                                else:
                                    strip.insert(0, of)
                                    v=(i-1)%3
                                    firstvertex=v
                                faces[nf]=0	# take face off list
                            else:
                                break

                else:	# Quads
                    striptype="Quad"
                    # Strip could maybe go two ways - try horzontally first
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

                    # Horizontally then Vertically
                    for hv in [0,1]:	# rotate 0 or 90
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
                                    faces[nf]=0	# take face off list
                                else:
                                    break
                        # not both horiontally and vertically
                        if len(strip)>1:
                            break

                if len(strip)>1:
                    print "Info:\tFound strip of %s %ss in Mesh \"%s\"" % (
                        len(strip), striptype, object.name)
                self.writeStrip(strip,firstvertex,name)
                name=0
                
        self.file.write("\n")	# Extra space after mesh for readability


    #------------------------------------------------------------------------
    # Return index of a face in faces which has the same number of edges, has
    # v and v+1 as vertices and faces the same way as the supplied face.
    def findFace (self,faces,face,v):
        n=len(face.v)
        v1=face.v[v]
        v2=face.v[(v+1)%n]
        uv1=face.uv[v]
        uv2=face.uv[(v+1)%n]
        for faceindex in v1.faces:
            if faces[faceindex] and len(faces[faceindex].v)==n:
                for i in range(n):
                    if  (faces[faceindex].v[i]==v2 and
                         faces[faceindex].v[(i+1)%n]==v1 and
                         faces[faceindex].uv[i].equals(uv2) and
                         faces[faceindex].uv[(i+1)%n].equals(uv1)):
                        return (faceindex,i)
        return (-1,-1)

    #------------------------------------------------------------------------
    # Write out a strip of Tris or Quads
    # Assumes all faces face the same way
    # Assumes whole strip is either Tris or Quads, not mix of both
    # Assumes whole strip is either smooth or flat, not mix of both
    # Assumes whole strip is either depth tested or not, not mix of both
    # Assumes that any "hard" faces are in a strip of length 1
    def writeStrip (self,strip,firstvertex,name):
        n=len(strip[0].v)
        
        smooth=0
        no_depth=0
        for face in strip:
            smooth|=(face.flags&Face.SMOOTH)
            no_depth|=(face.flags&Face.NO_DEPTH)
        self.updateFlags(smooth, no_depth)

        face=strip[0]
        
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
                if name:
                    self.file.write("\t\t// Mesh: %s\n" % name)
                else:
                    self.file.write("\t\t//\n")
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
                if name:
                    self.file.write("\t// Mesh: %s\n" % name)
                else:
                    self.file.write("\t//\n")

            for i in range(topright, topright-n, -1):
                if self.fileformat==7:
                    self.file.write("%s\t  %s\n" % (face.v[i%n], face.uv[i%n]))
                else:
                    self.file.write("%s\n" % face.v[i%n])

        else:	# len(strip)>1
            if self.debug:
                for f in strip:
                    print f

            if self.fileformat==7:
                if n==3:
                    self.file.write ("tri_fan %s" % (len(strip)+2))
                else:
                    self.file.write ("quad_strip %s" % ((len(strip)+1)*2))
            else:
                self.file.write ("%s\t" % -(len(strip)+1))
            if name:
                self.file.write("\t\t// Mesh: %s\n" % name)
            else:
                self.file.write("\t\t//\n")

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

    #------------------------------------------------------------------------
    def updateFlags(self,smooth,no_depth):
        if not self.fileformat==7:
            return	# v6 format doesn't support this stuff

        # For readability, write turn-offs before turn-ons
        # Note X-Plane parser requires a comment after attribute statements
        
        if self.smooth and not smooth:
            self.file.write("ATTR_shade_flat\t\t//\n\n")
        if self.no_depth and not no_depth:
            self.file.write("ATTR_depth\t\t//\n\n")
            
        if smooth and not self.smooth:
            self.file.write("ATTR_shade_smooth\t//\n\n")
        if no_depth and not self.no_depth:
            self.file.write("ATTR_no_depth\t\t//\n\n")
                
        self.smooth=smooth
        self.no_depth=no_depth

    
#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

if Blender.Get('version') < 230:
    print "Error:\tOBJ export failed, wrong blender version!"
    print "\tYou aren't running blender version 2.30 or greater"
    print "\tdownload a newer version from http://blender3d.org/"
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

