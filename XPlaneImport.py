#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane scenery (.obj)...'
Blender: 232
Group: 'Import'
Tooltip: 'Import an X-Plane scenery file (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane importer for blender 2.34 or above
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
#  - Import at cursor, not origin
#
# 2004-02-08 v1.12
#  - Fixed refusing to recognise DOS-mode v6 files
#  - Fixed triangle texture rotation with v6 files
#
# 2004-02-09 v1.13
#  - Fixed filename bug when texture file is a png
#
# 2004-02-29 v1.20
#  - Emulate Lines with faces
#  - Join adjacent faces into meshes for easier and faster editing
#
# 2004-03-24 v1.30
#  - Reduced duplicate vertex limit from 0.25 to 0.1 to handle smaller objects
#
# 2004-04-10 v1.40
#  - Reduced duplicate vertex limit to 0.01 to handle imported objects
#
# 2004-08-22 v1.50
#  - Reversed meaning of DYNAMIC flag, since it is set by default when
#    creating new faces in Blender
#
# 2004-08-28 v1.60
#  - Added support for double-sided faces
#  - Support importing files with multiple LODs
#
# 2004-08-28 v1.61
#  - Requires Blender 234 due to changed layer semantics of Blender fix #1212
#  - Display number of X-Plane objects on import and export
#
# 2004-08-29 v1.62
#  - Light and Line colours are floats
#
# 2004-08-30 v1.63
#  - Don't set alpha
#
# 2004-09-02 v1.70
#  - Try harder to preserve object names in comments
#
# 2004-09-04 v1.71
#
# 2004-09-10 v1.72
#
# 2004-10-10 v1.73
#  - Report line number on input error
#  - Reduced duplicate vertex limit to 0.001 for small objects eg cockpits
#
# 2004-10-17 v1.74
#
# 2004-11-01 v1.80
#  - Support for "quad_cockpit" using "Text" button
#

import sys
import Blender
from Blender import Object, NMesh, Lamp, Image, Material, Window

class ParseError(Exception):
    def __init__(self, type, value=""):
        self.type = type
        self.value = value
    HEADER = 0
    TOKEN  = 1
    INTEGER= 2
    FLOAT  = 3

class Token:
    "OBJ tokens"
    END7	= 0
    LIGHT	= 1
    LINE	= 2
    TRI		= 3
    QUAD	= 4
    QUAD_HARD	= 5
    SMOKE_BLACK	= 6
    SMOKE_WHITE	= 7
    QUAD_MOVIE	= 8
    POLYGON	= 9
    QUAD_STRIP	= 10
    TRI_STRIP	= 11
    TRI_FAN	= 12
    SHADE_FLAT	= 13
    SHADE_SMOOTH= 14
    AMBIENT_RGB	= 15
    DIFUSE_RGB	= 16
    SPECULAR_RGB= 17
    EMISSION_RGB= 18
    SHINY_RAT	= 19
    NO_DEPTH	= 20
    DEPTH	= 21
    LOD		= 22
    NO_CULL	= 23
    NOCULL	= 24
    CULL	= 25
    POLY_OS	= 26
    QUAD_COCKPIT= 27
    END6	= 99
    NAMES = [
        "end",
        "Light",
        "Line",
        "Tri",
        "Quad",
        "Quad_hard",
        "Smoke_Black",
        "Smoke_White",
        "Quad_Movie",
        "Polygon",
        "Quad_Strip",
        "Tri_Strip",
        "Tri_Fan",
        "ATTR_shade_flat",
        "ATTR_shade_smooth",
        "ATTR_ambient_rgb",
        "ATTR_difuse_rgb",
        "ATTR_specular_rgb",
        "ATTR_emission_rgb",
        "ATTR_shiny_rat",
        "ATTR_no_depth",
        "ATTR_depth",
        "ATTR_LOD",
        # 7.40+
        "ATTR_no_cull",
        "ATTR_nocull",	# Also seen
        "ATTR_cull",
        "ATTR_poly_os",
        # 8.00+
        "Quad_cockpit"
        ]

class Vertex:
    LIMIT=0.001	# max distance between vertices for them to be merged
    ROUND=1	# Precision
    
    def __init__(self, x, y, z):
        self.x=x
        self.y=y
        self.z=z

    def __str__(self):
        return "%s %s %s" % (round(self.x,Vertex.ROUND),
                             round(self.y,Vertex.ROUND),
                             round(self.z,Vertex.ROUND))
    
    def equals (self, v):
        if ((abs(self.x-v.x) < Vertex.LIMIT) and
            (abs(self.y-v.y) < Vertex.LIMIT) and
            (abs(self.z-v.z) < Vertex.LIMIT)):
            return 1
        else:
            return 0

class UV:
    ROUND=4

    def __init__(self, s, t):
        self.s=s
        self.t=t

    def __str__(self):
        return "%s %s" % (round(self.s,UV.ROUND), round(self.t,UV.ROUND))

class Face:
    # Flags
    HARD=1    
    NO_DEPTH=2
    DBLSIDED=4
    COCKPIT=8

    def __init__(self):
        self.v=[]
        self.uv=[]
        self.flags=0

    def addVertex(self, v):
        self.v.append(v)

    def addUV(self, uv):
        self.uv.append(uv)

    def checkDuplicateVertices(self):
    	for i in range(len(self.v)-1):
            for j in range(i+1,len(self.v)):
                if self.v[i].equals(self.v[j]):
                    self.v[i].x=(self.v[i].x+self.v[j].x)/2
                    self.v[i].y=(self.v[i].y+self.v[j].y)/2
                    self.v[i].z=(self.v[i].z+self.v[j].z)/2
                    del self.v[j]
                    # This is pretty arbitrary
                    self.uv[i].s=max(self.uv[i].s,self.uv[j].s)
                    self.uv[i].t=max(self.uv[i].t,self.uv[j].t)
                    del self.uv[j]
                    return

class Mesh:
    # Flags
    LAYERMASK=7
    DBLSIDED=8
    SMOOTH=16

    def __init__(self, name, faces=[], flags=0):
        self.name=name
        self.faces=faces
        self.flags=flags

    def addFaces(self, name, faces):
        if name != self.name:
            # no longer a standard X-Plane object
            self.name="Mesh"
        self.faces.extend(faces)

    #------------------------------------------------------------------------
    # do faces have any edges in common?
    def abut(self,faces):
        for face1 in self.faces:
            n1=len(face1.v)
            for i1 in range(n1):
                for face2 in faces:
                    n2=len(face2.v)
                    for i2 in range(n2):
                        if ((face1.v[i1].equals(face2.v[i2]) and
                             face1.v[(i1+1)%n1].equals(face2.v[(i2+1)%n2])) or
                            (face1.v[i1].equals(face2.v[(i2+1)%n2]) and
                             face1.v[(i1+1)%n1].equals(face2.v[i2]))):
                            return 1
        return 0
    
    #------------------------------------------------------------------------
    def doimport(self,scene,image,filename):
        mesh=NMesh.New(self.name)
        mesh.mode &= ~(NMesh.Modes.TWOSIDED|NMesh.Modes.AUTOSMOOTH)
        mesh.mode |= NMesh.Modes.NOVNORMALSFLIP
        if self.flags&Mesh.DBLSIDED:
            mesh.mode |= NMesh.Modes.TWOSIDED
        #if image:
        #    mesh.addMaterial(material)

        n=0
        centre=Vertex(0,0,0)
        for f in self.faces:
            for vertex in f.v:
                n+=1
                centre.x+=vertex.x
                centre.y+=vertex.y
                centre.z+=vertex.z
        centre.x=round(centre.x/n,Vertex.ROUND)
        centre.y=round(centre.y/n,Vertex.ROUND)
        centre.z=round(centre.z/n,Vertex.ROUND)
        
        for f in self.faces:
            face=NMesh.Face()
            face.mode &= ~(NMesh.FaceModes.TWOSIDE|NMesh.FaceModes.TEX|
                           NMesh.FaceModes.TILES|NMesh.FaceModes.DYNAMIC)
            #face.transp=NMesh.FaceTranspModes.ALPHA
            if not f.flags&Face.HARD:
                face.mode |= NMesh.FaceModes.DYNAMIC
            if f.flags&Face.NO_DEPTH:
                face.mode |= NMesh.FaceModes.TILES
            if f.flags&Face.DBLSIDED:
                face.mode |= NMesh.FaceModes.TWOSIDE
            if self.flags&Mesh.SMOOTH:
                face.smooth=1

            for v in f.v:
                rv=Vertex(v.x-centre.x,v.y-centre.y,v.z-centre.z)
                for nmv in mesh.verts:
                    if rv.equals(Vertex(nmv.co[0],nmv.co[1],nmv.co[2])):
                        nmv.co[0]=(nmv.co[0]+rv.x)/2
                        nmv.co[1]=(nmv.co[1]+rv.y)/2
                        nmv.co[2]=(nmv.co[2]+rv.z)/2
                        face.v.append(nmv)
                        break
                else:
                    nmv=NMesh.Vert(rv.x,rv.y,rv.z)
                    mesh.verts.append(nmv)
                    face.v.append(nmv)

            for uv in f.uv:
                face.uv.append((uv.s, uv.t))

            if f.flags&Face.COCKPIT:
                face.mode |= NMesh.FaceModes.TEX
                face.transp=NMesh.FaceTranspModes.ALPHA
                mesh.hasFaceUV(1)                
                l = filename.rfind(Blender.sys.dirsep)
                if l!=-1:
                    for extension in [".bmp", ".png"]:
                        cockpit=filename[:l+1]+"cockpit"+Blender.sys.dirsep+"-PANELS-"+Blender.sys.dirsep+"Panel"+extension
                        try:
                            file = open(cockpit, "rb")
                        except IOError:
                            pass
                        else:
                            file.close()
                            face.image = Image.Load(cockpit)
                            break
            elif image:
                face.mode |= NMesh.FaceModes.TEX
                face.image = image
                mesh.hasFaceUV(1)
                            
            mesh.faces.append(face)

        ob = Object.New("Mesh", self.name)
        ob.link(mesh)
        scene.link(ob)
        if self.flags&Mesh.LAYERMASK:
            ob.Layer=(self.flags&Mesh.LAYERMASK)
        cur=Window.GetCursorPos()
        ob.setLocation(centre.x+cur[0], centre.y+cur[1], centre.z+cur[2])
        mesh.update(1)
        

#------------------------------------------------------------------------
#-- OBJimport --
#------------------------------------------------------------------------
class OBJimport:
    LAYER=[0,1,2,4]

    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        self.aggressive=6	# how aggressively to merge meshes. Should be
        			# at least 1. 6 seems to cover most cases OK.
        
        #--- class private don't touch ---
        self.filename=filename
        self.linesemi=0.025
        self.lastpos=0		# for progress reporting
        self.lineno=0		# for error reporting
        self.filelen=0		# for progress reports
        self.fileformat=0	# 6 or 7
        self.image=0		# texture image, iff scenery has texture
        self.material=0		# only valid if self.image
        self.curmesh=[]		# unoutputted meshes
        self.nobj=0		# Number of X-Plane objects imported
        
        # random stuff
        self.whitespace=[" ","\t","\n","\r"]

        # flags controlling import
        self.comment=""
        self.smooth=0
        self.no_depth=0
        self.dblsided=0
        self.lod=0
        
    #------------------------------------------------------------------------
    def doimport(self):
        print "Starting OBJ import from " + self.filename
    
        self.file = open(self.filename, "rb")
        self.file.seek(0,2)
        self.filelen=self.file.tell()
        self.file.seek(0)
        Window.DrawProgressBar(0, "Opening ...")
        self.readHeader()
        self.readTexture()
        self.readObjects()
        Window.DrawProgressBar(1, "Finished")
        print "Finished - imported %s objects\n" % self.nobj

    #------------------------------------------------------------------------
    def getInput(self):
        input=""
        self.lastpos=self.file.tell()
        while 1:
            c=self.file.read(1)
            if not c:
            	raise ParseError(ParseError.TOKEN, "<EOF>")
            elif c in self.whitespace:
                if c == "\r":
                    self.lineno += 1
                # skip to first non-whitespace
                while 1:
                    pos = self.file.tell()
                    c = self.file.read(1)
                    if not c:
                        if self.verbose>1:
                            print "Input:\t\"%s\"" % input
                        return input
                    elif c == "\r":
                        self.lineno += 1
                    elif c == "/":
                        self.getCR()
                    elif not c in self.whitespace:
                        self.file.seek(pos)
                        if self.verbose>1:
                            print "Input:\t\"%s\"" % input
                        return input
            else:
                input+=c

    #------------------------------------------------------------------------
    def get7Token(self):
        c=self.getInput()
        u=c.lower()
        Window.DrawProgressBar(float(self.lastpos)*0.5/self.filelen,
                               "Importing %s%% ..." %
                               (self.lastpos*50/self.filelen))
        for i in range(len(Token.NAMES)):
            if u==Token.NAMES[i].lower():
                return i
        raise ParseError(ParseError.TOKEN, c)
        
    #------------------------------------------------------------------------
    def get6Token(self):
        c=self.getInput()
        Window.DrawProgressBar(float(self.lastpos)*0.5/self.filelen,
                               "Importing %s%% ..." %
                               (self.lastpos*50/self.filelen))
        try:
            return int(c)
        except ValueError:
            raise ParseError(ParseError.TOKEN, c)

    #------------------------------------------------------------------------
    def getInt(self):
        c=self.getInput()
        try:
            return int(c)
        except ValueError:
            raise ParseError(ParseError.INTEGER, c)
    
    #------------------------------------------------------------------------
    def getFloat(self):
        c=self.getInput()
        try:
            return float(c)
        except ValueError:
            raise ParseError(ParseError.FLOAT, c)
    
    #------------------------------------------------------------------------
    def getCol(self):
        v=[]
        for i in range(3):
            v.append(self.getFloat())
        return v

    #------------------------------------------------------------------------
    def getVertex(self):
        v=[]
        for i in range(3):
            v.append(self.getFloat())
        # Rotate to Blender format
        return Vertex(v[0],-v[2],v[1])
    
    #------------------------------------------------------------------------
    def getUV(self):
        uv=[]
        for i in range(2):
            uv.append(self.getFloat())
        return UV(uv[0],uv[1])
        
    #------------------------------------------------------------------------
    def getCR(self):
        self.comment=""
        while 1:
            c = self.file.read(1)
            if c == "\r":
                self.lineno += 1
                break
            elif c in ["", "\n"]:
                break
            self.comment += c
        self.comment = self.comment[1:].strip()
        # Export used to attach these prefixes to comments
        for c in ["Mesh: ", "Light: ", "Line: "]:
            if self.comment.find (c) == 0:
                self.comment=self.comment[len(c):]
        while 1:
            pos = self.file.tell()
            c = self.file.read(1)
            if c == "\r":
                self.lineno += 1
            elif c != "\n":
                break
        self.file.seek(pos)

    #------------------------------------------------------------------------
    def readHeader(self):
        c=self.file.read(1)
        if self.verbose>1:
            print "Input:\t\"%s\"" % c
        if c=="A" or c=="I":
            self.getCR()
            c = self.file.read(1)
            if self.verbose>1:
                print "Input:\t\"%s\"" % c
            if c=="2":
                self.getCR()
                self.fileformat=6
                if self.verbose:
                    print "Info:\tThis is an X-Plane v6 format file"
            elif c=="7" and self.file.read(2)=="00":
                self.getCR()
                if self.file.read(3)!="OBJ":
                    raise ParseError(ParseError.HEADER)
                self.getCR()
                self.fileformat=7
                if self.verbose:
                    print "Info:\tThis is an X-Plane v7 format file"
            else:
                raise ParseError(ParseError.HEADER)
        else:
            raise ParseError(ParseError.HEADER)

        # skip to first non-whitespace
        while 1:
            pos = self.file.tell()
            c = self.file.read(1)
            if not c:
                raise ParseError(HEADER)
            if c == "\r":
                self.lineno += 1
            if not c in self.whitespace:
                self.file.seek(pos)
                return
            
    #------------------------------------------------------------------------
    def readTexture (self):
        tex=self.getInput()
        if tex=="none":
            self.image=0
            if self.verbose:
                print "Info:\tNo texture"
            return

        basename=""
        for i in range(len(tex)):
            if tex[i]==":":
                basename+=Blender.sys.dirsep
            else:
                basename+=tex[i]

        l=self.filename.rfind(Blender.sys.dirsep)
        if l==-1:
            l=0
        else:
            l=l+1

        p=".."+Blender.sys.dirsep
        for extension in [".bmp", ".png"]:
            for prefix in ["",
                           p+"custom object textures"+Blender.sys.dirsep,
                           p+p+"custom object textures"+Blender.sys.dirsep,
                           p+p+p+"custom object textures"+Blender.sys.dirsep,
                           p+"AutoGen textures"+Blender.sys.dirsep,
                           p+p+"AutoGen textures"+Blender.sys.dirsep,
                           p+p+p+"AutoGen textures"+Blender.sys.dirsep]:
                texfilename=self.filename[:l]+prefix+basename+extension
                try:
                    file = open(texfilename, "rb")
                except IOError:
                    pass
                else:
                    file.close()
                    if self.verbose:
                        print "Info:\tUsing texture file \"%s\"" % texfilename
                    self.image = Image.Load(texfilename)
                
                    #self.material = Material.New(tex)
                    #self.material.mode |= Material.Modes.TEXFACE
                    #self.material.setAmb(0.25)	# Make more visible

                    return
            
        self.image=0
        print "Warn:\tTexture file \"%s\" not found" % basename
            
    #------------------------------------------------------------------------
    def readObjects (self):
        scene = Blender.Scene.getCurrent();

        if self.fileformat==7:
            while 1:
                t=self.get7Token()

                if t==Token.END7:
                    # write meshes
                    self.mergeMeshes()
                    for mesh in self.curmesh:
                        mesh.doimport(scene,self.image,self.filename)
                    return
                
                elif t==Token.LIGHT:
                    v=self.getVertex()
                    c=self.getCol()
                    self.addLamp(scene,v,c)

                elif t==Token.LINE:
                    v = []
                    c = []
                    for i in range(2):
                        v.append(self.getVertex())
                        c=self.getCol()	# use second colour value
                    self.addLine(scene,v,c)

                elif t==Token.TRI:
                    v = []
                    uv = []
                    for i in range(3):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    self.addTris(scene,t,v,uv)

                elif t in [Token.QUAD,
                           Token.QUAD_HARD,
                           Token.QUAD_MOVIE,
                           Token.QUAD_COCKPIT]:
                    v = []
                    uv = []
                    for i in range(4):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    self.addQuads(scene,t,v,uv,[3,2,1,0])
                                         
                elif t==Token.POLYGON:
                    # add centre point, duplicate first point, use Tri_Fan
                    v = []
                    uv = []
                    cv = [0,0,0]
                    cuv = [0,0]
                    n = self.getInt()
                    for i in range(n):
                        v.append(self.getVertex())
                        cv[0]+=v[i].x
                        cv[1]+=v[i].y
                        cv[2]+=v[i].z
                        uv.append(self.getUV())
                        cuv[0]+=uv[i].s
                        cuv[1]+=uv[i].t
                    cv[0]/=n
                    cv[1]/=n
                    cv[2]/=n
                    cuv[0]/=n
                    cuv[1]/=n
                    v.append(v[0])
                    uv.append(uv[0])
                    v.insert(0,Vertex(cv[0],cv[1],cv[2]))
                    uv.insert(0,UV(cuv[0],cuv[1]))
                    self.addTris(scene,t,v,uv)

                elif t==Token.QUAD_STRIP:
                    n = self.getInt()
                    v = []
                    uv = []
                    for i in range(n):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    self.addQuads(scene,t,v,uv,[1,0,2,3])
                        
                elif t==Token.TRI_FAN:
                    v = []
                    uv = []
                    n = self.getInt()
                    for i in range(n):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    self.addTris(scene,t,v,uv)
                    
                elif t==Token.SHADE_FLAT:
                    self.smooth = 0
                elif t==Token.SHADE_SMOOTH:
                    self.smooth = 1
                
                elif t==Token.DEPTH:
                    self.no_depth = 0
                elif t==Token.NO_DEPTH:
                    self.no_depth = 1
                
                elif t==Token.CULL:
                    self.dblsided = 0
                elif t in [Token.NO_CULL, Token.NOCULL]:
                    self.dblsided = 1

                elif t==Token.LOD:
                    x = self.getFloat()
                    self.getFloat()
                    if not self.lod:
                        print "Info:\tMultiple Levels Of Detail found"
                    if x>=3999:
                        self.lod=3
                    elif x>=999:
                        self.lod=2
                    else:
                        self.lod=1
                
                else:
                    print "Warn:\tIgnoring unsupported %s" % Token.NAMES[t]
                    if t==Token.LINE:
                        n=12
                    elif t in [Token.SMOKE_BLACK, Token.SMOKE_WHITE]:
                        n=4
                    elif t in [Token.AMBIENT_RGB, Token.DIFUSE_RGB,
                               Token.SPECULAR_RGB, Token.EMISSION_RGB]:
                        n=3
                    elif t in [Token.SHINY_RAT, Token.POLY_OS]:
                        n=1
                    else:
                        assert 0, "Can't parse type %s" % t

                    for i in range(n):
                        self.getFloat()
        else:	# v6
            while 1:
                t=self.get6Token()

                if t==Token.END6:
                    # write meshes
                    self.mergeMeshes()
                    for mesh in self.curmesh:
                        mesh.doimport(scene,self.image,self.filename)
                    return
    
                elif t==Token.LIGHT:
                    c=self.getCol()
                    v=self.getVertex()
                    self.addLamp(scene,v,c)
                
                elif t==Token.LINE:
                    v = []
                    c=self.getCol()
                    for i in range(2):
                        v.append(self.getVertex())
                    self.addLine(scene,v,c)

                elif t==Token.TRI:
                    v = []
                    uv = []
                    for i in range(4):
                        uv.append(self.getFloat())	# s s t t
                    for i in range(3):
                        v.append(self.getVertex())
                    # UV order appears to be arbitrary
                    self.addTris(scene,t,v,[UV(uv[1],uv[3]),
                                            UV(uv[1],uv[2]),
                                            UV(uv[0],uv[2])])
                elif t in [Token.QUAD,
                           Token.QUAD_HARD,
                           Token.QUAD_MOVIE]:
                    v = []
                    uv = []
                    for i in range(4):
                        uv.append(self.getFloat())
                    for i in range(4):
                        v.append(self.getVertex())
                    self.addQuads(scene,t,v,[UV(uv[1],uv[3]),
                                             UV(uv[1],uv[2]),
                                             UV(uv[0],uv[2]),
                                             UV(uv[0],uv[3])],
                                  [3,2,1,0])

                elif t<0:	# Quad strip
                    n = -t	# number of pairs
                    v = []
                    uv = []
                    for i in range(n):
                        v.append(self.getVertex())
                        v.append(self.getVertex())
                        s=self.getUV()		# s s t t
                        t=self.getUV()
                        uv.append(UV(s.s,t.s))
                        uv.append(UV(s.t,t.t))
                    self.addQuads(scene,Token.QUAD_STRIP,v,uv,[1,0,2,3])

                else:
                    print "Warn:\tIgnoring unsupported %s" % Token.NAMES[t]
                    if t==Token.LINE:
                        n=9
                    elif t in [Token.SMOKE_BLACK, Token.SMOKE_WHITE,
                               Token.QUAD, Token.QUAD_HARD, Token.QUAD_MOVIE]:
                        n=16
                    else:
                        assert 0, "Can't parse type %s" % t
                        
                    for i in range(n):
                        self.getFloat()

    #------------------------------------------------------------------------
    def addLamp(self, scene, v, c):
        if c[0]==99 and c[1]==99 and c[2]==99:
            c[0]=1.0
            c[1]=c[2]=0.0
            name="Pulse"
        elif c[0]==98 and c[1]==98 and c[2]==98:
            c[0]=c[1]=c[2]=1.0
            name="Strobe"
        elif c[0]==97 and c[1]==97 and c[2]==97:
            c[0]=c[1]=1.0
            c[2]=0.0
            name="Traffic"
        elif c[0]<0 or c[1]<0 or c[2]<0:
            c[0]=abs(c[0])/10.0
            c[1]=abs(c[1])/10.0
            c[2]=abs(c[2])/10.0
            name="Flash"
        else:
            c[0]=c[0]/10.0
            c[1]=c[1]/10.0
            c[2]=c[2]/10.0
            name="Light"

        if self.verbose:
            print "Info:\tImporting Lamp \"%s\"" % name
        lamp=Lamp.New("Lamp", name)
        lamp.col=c
        lamp.mode |= Lamp.Modes.Sphere	# stop lamp colouring whole object
        lamp.dist = 4.0
        ob = Object.New("Lamp", name)
        ob.link(lamp)
        scene.link(ob)
        if self.lod:
            ob.Layer=OBJimport.LAYER[self.lod]
        cur=Window.GetCursorPos()
        ob.setLocation(v.x+cur[0], v.y+cur[1], v.z+cur[2])
        self.nobj+=1
        
    #------------------------------------------------------------------------
    def addLine(self,scene,v,c):
        name=self.name("Line")
        if self.verbose:
            print "Info:\tImporting Line \"%s\"" % name

        # Round centre to integer to give easier positioning
        centre=Vertex(round((v[0].x+v[1].x)/2,0),
                      round((v[0].y+v[1].y)/2,0),
                      round((v[0].z+v[1].z)/2,0))
        d=Vertex(abs(v[0].x-v[1].x),abs(v[0].y-v[1].y),abs(v[0].z-v[1].z))

        if d.z>max(d.x,d.y):
            e=Vertex(self.linesemi,-self.linesemi,0)
        elif d.y>max(d.z,d.x):
            e=Vertex(-self.linesemi,0,self.linesemi)
        else:	# d.x>max(d.y,d.z):
            e=Vertex(0,self.linesemi,-self.linesemi)

        # 'Line's shouldn't be merged, so add immediately 
        mesh=NMesh.New(name)
        mesh.mode &= ~(NMesh.Modes.AUTOSMOOTH|NMesh.Modes.NOVNORMALSFLIP)
        mesh.mode |= NMesh.Modes.TWOSIDED

        face=NMesh.Face()
        face.mode &= ~(NMesh.FaceModes.TEX|NMesh.FaceModes.TILES)
        face.mode |= (NMesh.FaceModes.TWOSIDE|NMesh.FaceModes.DYNAMIC)

        mesh.verts.append(NMesh.Vert(v[0].x-centre.x+e.x,
                                     v[0].y-centre.y+e.y,
                                     v[0].z-centre.z+e.z))
        mesh.verts.append(NMesh.Vert(v[0].x-centre.x-e.x,
                                     v[0].y-centre.y-e.y,
                                     v[0].z-centre.z-e.z))
        mesh.verts.append(NMesh.Vert(v[1].x-centre.x-e.x,
                                     v[1].y-centre.y-e.y,
                                     v[1].z-centre.z-e.z))
        mesh.verts.append(NMesh.Vert(v[1].x-centre.x+e.x,
                                     v[1].y-centre.y+e.y,
                                     v[1].z-centre.z+e.z))
        for nmv in mesh.verts:
            face.v.append(nmv)

        mesh.materials.append(Material.New(name))
        mesh.materials[0].rgbCol=[c[0]/10.0,c[1]/10.0,c[2]/10.0]
        face.mat=0            
        mesh.faces.append(face)

        ob = Object.New("Mesh", name)
        ob.link(mesh)
        scene.link(ob)
        if self.lod:
            ob.Layer=OBJimport.LAYER[self.lod]
        cur=Window.GetCursorPos()
        ob.setLocation(centre.x+cur[0], centre.y+cur[1], centre.z+cur[2])
        mesh.update(1)
        self.nobj+=1

    #------------------------------------------------------------------------
    def addTris(self, scene, token, v, uv):
        # input v: list of co-ords, uv: corresponding list of uv points
        #	v[0] and uv[0] are common to every triangle
        name=self.name(Token.NAMES[token])
        if self.verbose:
            print "Info:\tImporting %s \"%s\"" % (Token.NAMES[token], name)
        nv=len(v)

        faces=[]
        for f in range(1,nv-1):
            face=Face()

            face.addVertex(v[0])
            face.addVertex(v[f+1])
            face.addVertex(v[f])
            face.addUV(uv[0])
            face.addUV(uv[f+1])
            face.addUV(uv[f])

            if self.no_depth:
                face.flags |= Face.NO_DEPTH
            if self.dblsided:
                face.flags |= Face.DBLSIDED
                
            faces.append(face)
            
        flags=0
        if self.dblsided:
            flags |= Mesh.DBLSIDED
        if self.smooth:
            flags |= Mesh.SMOOTH
        if self.lod:
            flags |= OBJimport.LAYER[self.lod]

        self.addToMesh(scene,name,faces,flags)
        self.nobj+=1

    #------------------------------------------------------------------------
    def addQuads(self, scene, token, v, uv, vorder):
        # input v: list of co-ords, uv: corresponding list of uv points
        #	vorder: order of vertices within each face

        name=self.name(Token.NAMES[token])
        if token==Token.QUAD_HARD:
            name=self.name(Token.NAMES[Token.QUAD])
        elif token==Token.QUAD_MOVIE:
            name=self.name("Movie")
        elif token==Token.QUAD_COCKPIT:
            name=self.name("Panel")
        if self.verbose:
            print "Info:\tImporting %s \"%s\"" % (Token.NAMES[token], name)
        nv=len(v)
        assert not nv%2, "Odd %s vertices in \"%s\"" % (nv, name)
        
        faces=[]
        for f in range(2,nv,2):
            face=Face()
            for i in range(4):
                face.addVertex(v[f-2+vorder[i]])
                face.addUV(uv[f-2+vorder[i]])

            # Some people use quads as tris to get round limitations in v6
            # in the way that textures are mapped to triangles. This is
            # unnecessary in v7 and screws up when we try to add the same
            # vertex twice. So manually remove any extra vertexs.
            face.checkDuplicateVertices()
            
            if token==Token.QUAD_HARD:
                face.flags |= Face.HARD
            if token==Token.QUAD_COCKPIT:
                face.flags |= Face.COCKPIT
            if self.no_depth:
                face.flags |= Face.NO_DEPTH
            if self.dblsided:
                face.flags |= Face.DBLSIDED
            
            faces.append(face)

        flags=0
        if self.dblsided:
            flags |= Mesh.DBLSIDED
        if self.smooth:
            flags |= Mesh.SMOOTH
        if self.lod:
            flags |= OBJimport.LAYER[self.lod]

        self.addToMesh(scene,name,faces,flags)
        self.nobj+=1

    #------------------------------------------------------------------------
    # add faces to existing or new mesh
    def addToMesh (self,scene,name,faces,flags):
        # New faces are added to an existing mesh if any new face has a common
        # edge with any existing face in the mesh (and existing and new faces
        # have the same flags).
        # We assume that all the new faces have common edges with each other
        # (and so can be safely added to the same mesh) since they all come
        # from the same X-Plane object).
        # Brute force and ignorance algorithm is used. But search most recently
        # added meshes first on the assumption of locality.
#        for m in range (len(self.curmesh)-1,-1,-1):
#            mesh=self.curmesh[m]
#            if mesh.abut(faces):
#                mesh.addFaces(faces)
#                return
            
        if self.curmesh and self.aggressive:
            if self.curmesh[-1].flags==flags and self.curmesh[-1].abut(faces):
                self.curmesh[-1].addFaces (name, faces)
                return
            
        # No common edge - new mesh required
        self.curmesh.append(Mesh(name, faces, flags))


    #------------------------------------------------------------------------
    # last chance - try to merge meshes that abut each other
    def mergeMeshes (self):
        m=len(self.curmesh)-2
        while m>=0:
            n=float(m)/len(self.curmesh)
            Window.DrawProgressBar(1-n/2,"Merging %s%% ..." % (100-int(50*n)))
            l=m+1
            # optimisation: take a copy of m's faces to prevent comparing any
            # newly merged faces multiple times - appears to be worth the cost
            facesm=[]
            for face in self.curmesh[m].faces:
                facesm.append(face)
            flags=self.curmesh[m].flags
            # sliding window
            while l<min(m+1+self.aggressive,len(self.curmesh)):
                if self.curmesh[l].flags==flags and self.curmesh[l].abut(facesm):
                    self.curmesh[m].addFaces("Mesh", self.curmesh[l].faces)
                    self.curmesh.pop(l)
                else:
                    l=l+1
            m=m-1

    #------------------------------------------------------------------------
    def name (self, fallback):
        if self.comment=='':
            name=fallback
        else:
            name=self.comment[:19].strip()
        return name

#------------------------------------------------------------------------
def file_callback (filename):
    obj=OBJimport(filename)
    try:
        obj.doimport()
    except ParseError, e:
        if e.type == ParseError.HEADER:
            msg="ERROR:\tThis is not a valid X-Plane v6 or v7 OBJ file\n"
        else:
            if e.type == ParseError.TOKEN:
                msg="ERROR:\tExpecting a Token,"
            elif e.type == ParseError.INTEGER:
                msg="ERROR:\tExpecting an integer,"
            elif e.type == ParseError.FLOAT:
                msg="ERROR:\tExpecting a number,"
            else:
                msg="ERROR:\tParse error,",
            msg=msg+" found \"%s\" at line %s\n" % (
                e.value, obj.lineno)
        Window.DrawProgressBar(1, "Error")
        print msg
        Blender.Draw.PupMenu(msg)
    obj.file.close()
    Blender.Redraw()

#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

if Blender.Get('version') < 234:
    msg="ERROR:\tRequires Blender version 2.34 or later."
    print msg
    Blender.Draw.PupMenu(msg)
else:
    Blender.Window.FileSelector(file_callback,"IMPORT .OBJ")
