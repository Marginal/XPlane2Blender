#------------------------------------------------------------------------
# X-Plane import/output utility classes for blender 2.34 or above
#
# Copyright (c) 2004, 2005 Jonathan Harris
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
# 2005-03-01 v2.00
#  - New file split out from other XPlane*.py scripts.
#

import sys
from math import sqrt, sin, cos
import Blender
from Blender import Types, Image
from Blender.Mathutils import Vector, Euler

class Vertex:
    LIMIT=0.001	# max distance between vertices for them to be merged
    ROUND=3	# Precision
    
    def __init__ (self, x, y=None, z=None, mm=None):
        self.faces=[]	# indices into face array

        if isinstance(x, Types.vectorType) or isinstance(x, Types.eulerType):
            mm=y
            z=x.z
            y=x.y
            x=x.x
        elif isinstance(x, list):
            mm=y
            z=x[2]
            y=x[1]
            x=x[0]
        elif y==None or z==None:
            raise TypeError

        if not mm:
            self.x=x
            self.y=y
            self.z=z
        else:	# apply scale, translate and swap axis
            self.x=round(mm[0][0]*x + mm[1][0]*y + mm[2][0]*z + mm[3][0],
                         Vertex.ROUND)
            self.y=round(mm[0][2]*x + mm[1][2]*y + mm[2][2]*z + mm[3][2],
                         Vertex.ROUND)
            self.z=-round(mm[0][1]*x + mm[1][1]*y + mm[2][1]*z + mm[3][1],
                          Vertex.ROUND)
            
    def __str__ (self):
        return "%8.3f %8.3f %8.3f" % (
            round(self.x, Vertex.ROUND),
            round(self.y, Vertex.ROUND),
            round(self.z, Vertex.ROUND))
    
    def __add__ (self, right):
        return Vertex(self.x+right.x, self.y+right.y, self.z+right.z)
        
    def __sub__ (self, right):
        return Vertex(self.x-right.x, self.y-right.y, self.z-right.z)
        
    def __mul__ (self, right):
        return Vertex(self.x*right, self.y*right, self.z*right)
    
    def __rmul__ (self, left):
        return Vertex(self.x*left, self.y*left, self.z*left)
    
    def __div__ (self, right):
        return Vertex(self.x/right, self.y/right, self.z/right)
    
    def __neg__ (self):
        return Vertex(-self.x, -self.y, -self.z)

    def equals (self, v, fudge=LIMIT):
        if ((abs(self.x-v.x) <= fudge) and
            (abs(self.y-v.y) <= fudge) and
            (abs(self.z-v.z) <= fudge)):
            return True
        else:
            return False

    def toVector (self, n):
        v=[self.x, self.y]
        if n==3:
            v.append(self.z)
        elif n==4:
            v.extend([self.z, 1.0])
        else:
            raise AttributeError
        return Vector(v)

    def toEuler (self, n):
        v=[self.x, self.y]
        if n==3:
            v.append(self.z)
        elif n==4:
            v.extend([self.z, 1.0])
        else:
            raise AttributeError
        return Euler(v)

    def normalize (self):
        hyp=sqrt(self.x*self.x + self.y*self.y + self.z*self.z)
        return self/hyp

    def addFace (self, v):
        self.faces.append(v)


class UV:
    LIMIT=0.008	# = 1 pixel in 128, 2 pixels in 256, etc
    ROUND=4

    def __init__(self, s, t=None):
        if isinstance(s, Types.vectorType):
            self.s=s.x
            self.t=s.y
        elif isinstance(s, list):
            self.s=s[0]
            self.t=s[1]
        elif t!=None:
            self.s=s
            self.t=t
        else:
            raise TypeError

    def __str__(self):
        return "%-6s %-6s" % (round(self.s,UV.ROUND), round(self.t,UV.ROUND))

    def __add__ (self, right):
        return UV(self.s+right.s, self.t+right.t)

    def __sub__ (self, right):
        return UV(self.s-right.s, self.t-right.t)

    def __mul__ (self, right):
        return UV(self.s*right.s, self.t*right.t)

    def __div__ (self, right):
        if isinstance(right, int):
            return UV(self.s/right, self.t/right)
        else:
            return UV(self.s/right.s, self.t/right.t)

    def equals (self, uv):
        if ((abs(self.s-uv.s) <= UV.LIMIT) and
            (abs(self.t-uv.t) <= UV.LIMIT)):
            return 1
        else:
            return 0

class Face:
    # Flags in v7 sort order
    HARD=1
    TWOSIDE=2
    FLAT=4
    ALPHA=8	# Must be 2nd last
    PANEL=16	# Must be last
    BUCKET=HARD|TWOSIDE|FLAT|ALPHA|PANEL	# For v7 export
    TILES=32	# Not output in v7

    def __init__ (self):
        self.v=[]
        self.uv=[]
        self.flags=0
        self.kosher=0	# Hack! True iff panel and within 1024x768

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

    def removeDuplicateVertices(self):
        i=0
        while i < len(self.v)-1:
            j=i+1
            while j < len(self.v):
                if self.v[i].equals(self.v[j]) and self.uv[i].equals(self.uv[j]):
                    self.v[i].x=round((self.v[i].x+self.v[j].x)/2,Vertex.ROUND)
                    self.v[i].y=round((self.v[i].y+self.v[j].y)/2,Vertex.ROUND)
                    self.v[i].z=round((self.v[i].z+self.v[j].z)/2,Vertex.ROUND)
                    del self.v[j]
                    self.uv[i].s=round((self.uv[i].s+self.uv[j].s)/2,UV.ROUND)
                    self.uv[i].t=round((self.uv[i].t+self.uv[j].t)/2,UV.ROUND)
                    del self.uv[j]
                else:
                    j=j+1
            i=i+1
        return len(self.v)


def findTex(basefile, texture, subdirs):
    texdir=basefile
    for l in range(5):
        q=texdir[:-1].rfind(Blender.sys.dirsep)
        if q==-1:
            return
        texdir=texdir[:q+1]

        for subdir in subdirs:
            # Handle empty subdir
            if subdir:
                sd=subdir+Blender.sys.dirsep
            for extension in ['.bmp', '.png']:
                try:
                    return Image.Load(texdir+sd+texture+extension)
                except IOError:
                    pass
    return None

