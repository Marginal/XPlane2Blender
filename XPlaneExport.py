#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane'
Blender: 230
Group: 'Export'
Tooltip: 'Export to X-Plane file format (.obj)'
"""
#------------------------------------------------------------------------
# X-Plane exporter for blender 2.32 or above, version 1.1
#
# Author: Jonathan Harris <x-plane@marginal.org.uk>
#
# Latest version: http://marginal.org.uk/x-plane
#
# See XPlaneReadme.txt for usage
#
# Notes:
#  - Output filename is same as current blender file with .obj extension
#  - Error messages go to the Blender console window
#
# 2004-01-25 v0.1 by Jonathan Harris <x-plane@marginal.org.uk>
#  - First version, based on v1.31 of wrl2export.py <rick@vrmlworld.net>
#
# 2004-02-01 v1.0 by Jonathan Harris <x-plane@marginal.org.uk>
#  - First public version
#
# 2004-02-01 v1.1 by Jonathan Harris <x-plane@marginal.org.uk>
#  - Updated for Blender 2.32
#

import sys
import Blender
from Blender import NMesh, Lamp, Draw
from string import *

#------------------------------------------------------------------------
#-- OBJexport --
#------------------------------------------------------------------------
class OBJexport:
    #------------------------------------------------------------------------
    def __init__(self, filename):
        #--- public you can change these ---
        self.verbose=0     # level of verbosity in console 0-none, 1-some, 2-most
        self.vp=2          # decimals for vertex coordinate values
        self.tp=3          # decimals for texture coordinate values
        self.fileformat=7  # export v6 or v7
        
        #--- class private don't touch ---
        self.filename=filename
        self.texture=""

        if sys.platform=="win32":
            self.dirsep="\\"
        else:
            self.dirsep="/"

    #------------------------------------------------------------------------
    def export(self, scene):
        if not self.checkFile():
            return
        print "Starting OBJ export to " + self.filename
    
        theObjects = []
        theObjects = scene.getChildren()

        self.getTexture (theObjects)
        
        self.file = open(self.filename, "w")
        self.writeHeader()
        self.writeObjects(theObjects)
        self.file.close()
        
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
        banner="Exported from blender3d using XPlane2Blender - http://marginal.org.uk/x-plane"
        if self.fileformat==7:
            self.file.write("I\n700\t// %s\nOBJ\n\n" % banner)
        else:
            self.file.write("I\n2\t// %s\n\n" % banner)
        self.file.write("%s\t// texture\n\n\n" % self.texture)

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
                            if (not texture) or (lower(texture) ==
                                                 lower(face.image.filename)):
                                texture = face.image.filename
                                texlist.append(lower(texture))
                            else:
                                if not erroring:
                                    erroring=1
                                    print "Warn:\tOBJ format supports one texture, but multiple texture files found:"
                                    print "\t\"%s\"" % texture
                                if not lower(face.image.filename) in texlist:
                                    texlist.append(lower(face.image.filename))
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

        if lower(self.texture)[-4:] == ".bmp":
            self.texture = self.texture[:-4]

        # try to guess correct texture path
        for prefix in ["custom object textures", "autogen textures"]:
            l=rfind(lower(self.texture), prefix)
            if l!=-1:
                self.texture = self.texture[l+len(prefix)+1:]
                return
            
    #------------------------------------------------------------------------
    def writeObjects (self, theObjects):
        nobj=len(theObjects)
        for o in range (nobj-1,-1,-1):
            object=theObjects[o]
            objType=object.getType()

            if objType == "Mesh":
                self.writeMesh(object)
            elif objType == "Lamp":
                self.writeLamp(object)
            else:
                print "Warn:\tIgnoring unsupported %s \"%s\"" % (
                    object.getType(), object.name)
        if self.fileformat==7:
            self.file.write("end\t// eof\n")
        else:
            self.file.write("99\t// eof\n")

    #------------------------------------------------------------------------
    def writeLamp(self, object):
        lamp=Lamp.Get(object.data.getName())
        name=lamp.getName()
        
        if lamp.getType() != Lamp.Types.Lamp:
            print "Info:\tIgnoring spot/sun/hemi \"%s\"" % name
        else:
            if self.verbose:
                print "Info:\tExporting Lamp \""+name+"\""

            uname=upper(name)
            c=[0,0,0]
            if not find(uname, "PULSE"):
                c[0]=c[1]=c[2]=99
            elif not find(uname, "STROBE"):
                c[0]=c[1]=c[2]=98
            elif not find(uname, "TRAFFIC"):
                c[0]=c[1]=c[2]=97
            elif not find(uname, "FLASH"):
                c[0]=int(lamp.col[0]*-10)
                c[1]=int(lamp.col[1]*-10)
                c[2]=int(lamp.col[2]*-10)
            else:
                c[0]=int(lamp.col[0]*10)
                c[1]=int(lamp.col[1]*10)
                c[2]=int(lamp.col[2]*10)
                    
            v=self.rotVertex(object.getMatrix(), (0,0,0))
            if self.fileformat==7:
                self.file.write("light\t\t// Lamp: %s\n" % name)
                self.file.write("%s %s %s \t%s %s %s\n\n\n" % (
                    round(v[0], self.vp),
                    round(v[1], self.vp),
                    round(v[2], self.vp),
                    c[0], c[1], c[2]))
            else:
                self.file.write("1 %s %s %s\t// Lamp: %s\n" % (
                    c[0], c[1], c[2],
                    name))
                self.writeVertex(v)
                self.file.write("\n\n")
            
    #------------------------------------------------------------------------
    def writeMesh(self, object):
        if self.verbose:
            print "Info:\tExporting Mesh \""+object.name+"\""

        mesh=object.getData()
        mm=object.getMatrix()
        smooth=0	# flat is the default
        no_depth=0	# depth testing is the default
        first=1		# first face in this mesh

        for face in mesh.faces:
            n=len(face.v)
            if (n != 3) and (n != 4):
                print "Warn:\tIgnoring %s-edged face in mesh \"%s\"" % (
                    n, object.name)
            else:
                if (face.mode & NMesh.FaceModes.TWOSIDE):
                    print "Warn:\tMesh \""+object.name+"\" has double-sided face"

                if self.fileformat==7 and face.smooth and not smooth:
                    smooth=1
                    # X-Plane parser requires a comment
                    self.file.write("ATTR_shade_smooth\t// smooth\n\n")
                elif not face.smooth and smooth:
                    smooth=0
                    self.file.write("ATTR_shade_flat\t// solid\n\n")

                if self.fileformat==7 and (face.mode & NMesh.FaceModes.TILES) and not no_depth:
                    no_depth=1
                    # X-Plane parser requires a comment
                    self.file.write("ATTR_no_depth\t// no depth testing\n\n")
                elif not (face.mode & NMesh.FaceModes.TILES) and no_depth:
                    no_depth=0
                    self.file.write("ATTR_depth\t// depth testing\n\n")
                    
                # When viewing the visible side of a face
                #  - Blender writes vertices anticlockwise
                #  - XPlane expects clockwise, starting with top right
                # So find top right vertex, then write in reverse order
                if mesh.hasFaceUV() and (face.mode & NMesh.FaceModes.TEX):
                    hasTex = 1
                    maxX=maxY=-99
                    for i in range(n):
                        if (maxX<face.uv[i][0]):
                            maxX=face.uv[i][0]
                        if (maxY<face.uv[i][1]):
                            maxY=face.uv[i][1]
                        if (maxX==face.uv[i][0]) and (maxY==face.uv[i][1]):
                            topright=i
                else:
                    hasTex = 0
                    topright=n-1
                            
                if self.fileformat==7:
                    if (n == 3):
                        self.file.write ("tri\t")
                    elif (face.mode & NMesh.FaceModes.DYNAMIC):
                        self.file.write ("quad_hard")
                    else:
                        self.file.write ("quad\t")
                else:
                    if (n==4) and (face.mode & NMesh.FaceModes.DYNAMIC):
                        poly=5	# make quad "hard"
                    else:
                        poly=n
                    if not hasTex:
                        self.file.write("%s 0 0 0 0" % poly)
                    else:
                        self.file.write("%s %s %s %s %s" % (
                            poly,
                            round(face.uv[(topright-2)%n][0], self.tp),
                            round(face.uv[ topright     ][0], self.tp),
                            round(face.uv[(topright-2)%n][1], self.tp),
                            round(face.uv[ topright     ][1], self.tp)))

                if first:
                    self.file.write("\t// Mesh: %s\n" % object.name)
                    first = 0
                else:
                    self.file.write("\n")

                for i in range(topright, topright-n, -1):
                    v=self.rotVertex(mm, face.v[i%n])
                    if self.fileformat==7:
                        if hasTex:
                            self.writeVertexUV(v, face.uv[i%n])
                        else:
                            self.writeVertexUV(v, (0,0))
                    else:
                        self.writeVertex(v)

                self.file.write("\n")

        if smooth:
            self.file.write("ATTR_shade_flat\t// solid\n\n")
            
        if no_depth:
            self.file.write("ATTR_depth\t// depth testing\n\n")
            
        self.file.write("\n")

    #------------------------------------------------------------------------

    def rotVertex(self, mm, v):
        return [
            mm[0][0]*v[0] + mm[1][0]*v[1] + mm[2][0]*v[2] + mm[3][0],
            mm[0][2]*v[0] + mm[1][2]*v[1] + mm[2][2]*v[2] + mm[3][2],
            -(mm[0][1]*v[0] + mm[1][1]*v[1] + mm[2][1]*v[2] + mm[3][1])
            ]

    #------------------------------------------------------------------------

    def writeVertex(self, v):
        self.file.write("%s %s %s\n" % (
            round(v[0], self.vp),
            round(v[1], self.vp),
            round(v[2], self.vp)))

    #------------------------------------------------------------------------

    def writeVertexUV(self, v, uv):
        self.file.write("%s %s %s\t%s %s\n" % (
            round(v[0], self.vp),
            round(v[1], self.vp),
            round(v[2], self.vp),
            round(uv[0], self.tp),
            round(uv[1], self.tp)))

#enddef
    
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

