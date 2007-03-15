#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane...'
Blender: 230
Group: 'Import'
Tooltip: 'Import X-Plane file format (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane importer for blender 2.32 or above, version 1.13
#
# Copyright (c) 2004 Jonathan Harris
# 
# Mail: <x-plane@marginal.org.uk>
# Web: http://marginal.org.uk/x-plane
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
    END6	= 99
    NAMES = ["end",
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
             "ATTR_LOD"]

#------------------------------------------------------------------------
#-- OBJimport --
#------------------------------------------------------------------------
class OBJimport:
    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0	# level of verbosity in console 0-none, 1-some, 2-most
        
        #--- class private don't touch ---
        self.filename=filename
        self.lastpos=0	# for error reporting
        self.fileformat=0
        self.image=0
        self.material=0
        self.whitespace=[" ","\t","\n","\r"]

        if sys.platform=="win32":
            self.dirsep="\\"
        else:
            self.dirsep="/"

        # flags controlling import
        self.smooth=0
        self.no_depth=0
        self.lod=0
        
    #------------------------------------------------------------------------
    def doimport(self):
        print "Starting OBJ import from " + self.filename
    
        self.file = open(self.filename, "rb")
        self.readHeader()
        self.readTexture()
        self.readObjects()
        print "Finished\n"

    #------------------------------------------------------------------------
    def getInput(self):
        input=""
        self.lastpos=self.file.tell()
        while 1:
            c=self.file.read(1)
            if not c:
            	raise ParseError(ParseError.TOKEN, "<EOF>")
            elif c in self.whitespace:
                # skip to first non-whitespace
                while 1:
                    pos=self.file.tell()
                    c=self.file.read(1)
                    if not c:
                        if self.verbose>1:
                            print "Input:\t\"%s\"" % input
                        return input
                    elif c=="/":
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

        for i in range(len(Token.NAMES)):
            if u==Token.NAMES[i].lower():
                return i
        raise ParseError(ParseError.TOKEN, c)
        
    #------------------------------------------------------------------------
    def get6Token(self):
        c=self.getInput()
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
            v.append(self.getInt())
        return v

    #------------------------------------------------------------------------
    def getVertex(self):
        v=[]
        for i in range(3):
            v.append(self.getFloat())
        # Rotate to Blender format
        return [v[0],-v[2],v[1]]
    
    #------------------------------------------------------------------------
    def getUV(self):
        uv=[]
        for i in range(2):
            uv.append(self.getFloat())
        return uv
        
    #------------------------------------------------------------------------
    def getCR(self):
        while self.file.read(1) not in ["", "\n", "\r"]:
            pass
        pos=self.file.tell()
        while self.file.read(1) in ["\n", "\r"]:
            pos=self.file.tell()
        self.file.seek(pos)

    #------------------------------------------------------------------------
    def readHeader(self):
        c=self.file.read(1)
        if self.verbose>1:
            print "Input:\t\"%s\"" % c
        if c=="A" or c=="I":
            self.getCR()
            c=self.file.read(1)
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
            pos=self.file.tell()
            c=self.file.read(1)
            if not c:
                raise ParseError(HEADER)
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
                basename+=self.dirsep
            else:
                basename+=tex[i]

        l=self.filename.rfind(self.dirsep)
        if l==-1:
            l=0
        else:
            l=l+1

        p=".."+self.dirsep
        for extension in [".bmp", ".png"]:
            for prefix in ["",
                           p+"custom object textures"+self.dirsep,
                           p+p+"custom object textures"+self.dirsep,
                           p+p+p+"custom object textures"+self.dirsep,
                           p+"AutoGen textures"+self.dirsep,
                           p+p+"AutoGen textures"+self.dirsep,
                           p+p+p+"AutoGen textures"+self.dirsep]:
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
                
                    self.material = Material.New(tex)
                    self.material.mode |= Material.Modes.TEXFACE
                    self.material.setAmb(0.25)	# Make more visible

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
                    return
                
                elif t==Token.LIGHT:
                    v=self.getVertex()
                    c=self.getCol()
                    if not self.lod:
                        self.addLamp(scene,v,c)

                elif t==Token.TRI:
                    v = []
                    uv = []
                    for i in range(3):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    if not self.lod:
                        self.addTris(scene,t,3,v,uv)

                elif t in [Token.QUAD,
                           Token.QUAD_HARD,
                           Token.QUAD_MOVIE]:
                    v = []
                    uv = []
                    for i in range(4):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    if not self.lod:
                        self.addQuads(scene,t,4,v,uv,[3,2,1,0])
                                         
                elif t==Token.POLYGON:
                    # add centre point, duplicate first point, use Tri_Fan
                    v = []
                    uv = []
                    cv = [0,0,0]
                    cuv = [0,0]
                    n = self.getInt()
                    for i in range(n):
                        v.append(self.getVertex())
                        cv[0]+=v[i][0]
                        cv[1]+=v[i][1]
                        cv[2]+=v[i][2]
                        uv.append(self.getUV())
                        cuv[0]+=uv[i][0]
                        cuv[1]+=uv[i][1]
                    if not self.lod:
                        cv[0]/=n
                        cv[1]/=n
                        cv[2]/=n
                        cuv[0]/=n
                        cuv[1]/=n
                        v.append(v[0])
                        uv.append(uv[0])
                        v.insert(0,cv)
                        uv.insert(0,cuv)
                        self.addTris(scene,t,n+2,v,uv)

                elif t==Token.QUAD_STRIP:
                    n = self.getInt()
                    v = []
                    uv = []
                    for i in range(n):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    if not self.lod:
                        self.addQuads(scene,t,n,v,uv,[1,0,2,3])
                        
                elif t==Token.TRI_FAN:
                    v = []
                    uv = []
                    n = self.getInt()
                    for i in range(n):
                        v.append(self.getVertex())
                        uv.append(self.getUV())
                    if not self.lod:
                        self.addTris(scene,t,n,v,uv)
                    
                elif t==Token.SHADE_FLAT:
                    self.smooth = 0
                elif t==Token.SHADE_SMOOTH:
                    self.smooth = 1
                
                elif t==Token.DEPTH:
                    self.no_depth = 0
                elif t==Token.NO_DEPTH:
                    self.no_depth = 1
                
                elif t==Token.LOD:
                    x = self.getInt()
                    self.getInt()
                    if (x):
                        self.lod = x
                        print "Warn:\tNon-zero LOD not supported: Ignoring following objects"
                    elif self.lod:
                        self.lod = 0
                        print "Info:\tLOD reset: Stopped ignoring objects"
                
                elif t in [Token.LINE, Token.SMOKE_BLACK, Token.SMOKE_WHITE,
                           Token.AMBIENT_RGB, Token.DIFUSE_RGB,
                           Token.SPECULAR_RGB, Token.EMISSION_RGB,
                           Token.SHINY_RAT]:
                    print "Warn:\tIgnoring unsupported %s" % Token.NAMES[t]
                    if t==Token.LINE:
                        n=12
                    elif t in [Token.SMOKE_BLACK, Token.SMOKE_WHITE]:
                        n=4
                    elif t in [Token.AMBIENT_RGB, Token.DIFUSE_RGB,
                               Token.SPECULAR_RGB, Token.EMISSION_RGB]:
                        n=3
                    else:
                        n=1
                    for i in range(n):
                        self.getFloat()
                else:
                    print "Error:\tInternal error, object type %s" % t
        else:	# v6
            while 1:
                t=self.get6Token()

                if t==Token.END6:
                    return
    
                elif t==Token.LIGHT:
                    c=self.getCol()
                    v=self.getVertex()
                    self.addLamp(scene,v,c)
                
                elif t==Token.TRI:
                    v = []
                    uv = []
                    for i in range(4):
                        uv.append(self.getFloat())	# s s t t
                    for i in range(3):
                        v.append(self.getVertex())
                    # UV order appears to be arbitrary
                    self.addTris(scene,t,3,v,[[uv[1],uv[3]],
                                              [uv[1],uv[2]],
                                              [uv[0],uv[2]]])
                elif t in [Token.QUAD,
                           Token.QUAD_HARD,
                           Token.QUAD_MOVIE]:
                    v = []
                    uv = []
                    for i in range(4):
                        uv.append(self.getFloat())
                    for i in range(4):
                        v.append(self.getVertex())
                    self.addQuads(scene,t,4,v, [[uv[1],uv[3]],
                                                [uv[1],uv[2]],
                                                [uv[0],uv[2]],
                                                [uv[0],uv[3]]],
                                  [3,2,1,0])

                elif t<0:	# Quad strip
                    n = -t
                    v = []
                    uv = []
                    for i in range(n):
                        v.append(self.getVertex())
                        v.append(self.getVertex())
                        s=self.getUV()
                        t=self.getUV()
                        uv.append([s[0],t[0]])
                        uv.append([s[1],t[1]])
                    self.addQuads(scene,Token.QUAD_STRIP,n*2,v,uv,[1,0,2,3])

                elif t in [Token.LINE, Token.SMOKE_BLACK, Token.SMOKE_WHITE]:
                    print "Warn:\tIgnoring unsupported %s" % Token.NAMES[t]
                    if t==Token.LINE:
                        n=9
                    else:
                        n=16
                    for i in range(n):
                        self.getFloat()
                else:
                    print "Error:\tInternal error, object type %s" % t
            

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
        lamp.dist = 10.0
        ob = Object.New("Lamp", name)
        ob.link(lamp)
        scene.link(ob)
        self.locate(ob,v)
        
    #------------------------------------------------------------------------
    def addQuads(self, scene, token, nv, v, uv, vorder):
        name=Token.NAMES[token]
        if nv%2:
            print "Error:\t%s has odd number of vertices - %s" % (name, nv)
        else:
            if token==Token.QUAD_HARD:
                name=Token.NAMES[Token.QUAD]
            elif token==Token.QUAD_MOVIE:
                name="Movie"
            if self.verbose:
                print "Info:\tImporting %s" % name
        
            mesh=NMesh.New(name)
            mesh.mode &= ~(NMesh.Modes.TWOSIDED|NMesh.Modes.AUTOSMOOTH)
            mesh.mode |= NMesh.Modes.NOVNORMALSFLIP

            centre=[0,0,0]
            for i in range(nv):
                centre[0]+=v[i][0]
                centre[1]+=v[i][1]
                centre[2]+=v[i][2]

            centre[0]/=nv
            centre[1]/=nv
            centre[2]/=nv

            for i in range(nv):
                mesh.verts.append(NMesh.Vert(v[i][0]-centre[0],
                                             v[i][1]-centre[1],
                                             v[i][2]-centre[2]))

            for f in range(2,nv,2):
                n=4
                face=NMesh.Face()
                face.smooth=self.smooth
                face.mode &= ~NMesh.FaceModes.TWOSIDE
                if self.no_depth:
                    face.mode |= NMesh.FaceModes.TILES
                else:
                    face.mode &= ~NMesh.FaceModes.TILES
                if token==Token.QUAD_HARD:
                    face.mode |= NMesh.FaceModes.DYNAMIC
                else:
                    face.mode &= ~NMesh.FaceModes.DYNAMIC

                for i in range(n):
                    face.v.append(mesh.verts[f-2+vorder[i]])

                if self.image:
                    hasTex=0
                    for i in range(f-n/2,f+n/2):
                        if uv[i][0] or uv[1][1]:
                            hasTex=1
                    if hasTex:
                        face.mode |= NMesh.FaceModes.TEX
                        face.image = self.image
                        for i in range(4):
                            face.uv.append((uv[f-2+vorder[i]][0],
                                            uv[f-2+vorder[i]][1]))
                        mesh.hasFaceUV(1)
                            
                mesh.faces.append(face)

            if self.image:
                mesh.addMaterial(self.material)

            ob = Object.New("Mesh", name)
            ob.link(mesh)
            scene.link(ob)
            self.locate(ob,centre)
            mesh.update(1)

    #------------------------------------------------------------------------
    def addTris(self, scene, token, nv, v, uv):
        name=Token.NAMES[token]
        if self.verbose:
            print "Info:\tImporting %s" % name
        
        mesh=NMesh.New(name)
        mesh.mode &= ~(NMesh.Modes.TWOSIDED|NMesh.Modes.AUTOSMOOTH)
        mesh.mode |= NMesh.Modes.NOVNORMALSFLIP

        centre=v[0]
        for i in range(nv):
            mesh.verts.append(NMesh.Vert(v[i][0]-centre[0],
                                         v[i][1]-centre[1],
                                         v[i][2]-centre[2]))

        for f in range(1,nv-1):
            face=NMesh.Face()
            face.smooth=self.smooth
            face.mode &= ~(NMesh.FaceModes.TWOSIDE|NMesh.FaceModes.DYNAMIC)

            face.v.append(mesh.verts[0  ])
            face.v.append(mesh.verts[f+1])
            face.v.append(mesh.verts[f  ])

            if self.image:
                hasTex=0
                for i in range(f,f+2):
                    if uv[i][0] or uv[1][1]:
                        hasTex=1
                if hasTex:
                    face.mode |= NMesh.FaceModes.TEX
                    face.image = self.image
                    face.uv.append((uv[0  ][0], uv[0  ][1]))
                    face.uv.append((uv[f+1][0], uv[f+1][1]))
                    face.uv.append((uv[f  ][0], uv[f  ][1]))
                    mesh.hasFaceUV(1)
                            
            mesh.faces.append(face)

        if self.image:
            mesh.addMaterial(self.material)
            
        ob = Object.New("Mesh", name)
        ob.link(mesh)
        scene.link(ob)
        self.locate(ob,centre)
        mesh.update(1)

    #------------------------------------------------------------------------
    def locate (self,object,v):
        c=Window.GetCursorPos()
        object.setLocation(v[0]+c[0], v[1]+c[1], v[2]+c[2])

#------------------------------------------------------------------------
def file_callback (filename):
    obj=OBJimport(filename)
    try:
        obj.doimport()
    except ParseError, e:
        if e.type == ParseError.HEADER:
            print "Error:\tNot an X-Plane v6 or v7 OBJ file\n"
        else:
            if e.type == ParseError.TOKEN:
                print "Error:\tExpecting a Token,",
            elif e.type == ParseError.INTEGER:
                print "Error:\tExpecting an integer,",
            elif e.type == ParseError.FLOAT:
                print "Error:\tExpecting a number,",
            else:
                print "Error:\tParse error,",
            print "found \"%s\" at file offset %s\n" % (
                e.value, obj.lastpos)
    obj.file.close()
    Blender.Redraw()

#------------------------------------------------------------------------
# main routine
#------------------------------------------------------------------------

if Blender.Get('version') < 230:
    print "Error:\tOBJ import failed, wrong blender version!"
    print "\tYou aren't running blender version 2.30 or greater"
    print "\tdownload a newer version from http://blender3d.org/"
else:
    Blender.Window.FileSelector(file_callback,"IMPORT .OBJ")

