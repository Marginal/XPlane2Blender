#!BPY
""" Registration info for Blender menus:
Name: 'X-Plane panel regions...'
Blender: 243
Group: 'Image'
Tooltip: 'Manage X-Plane cockpit panel regions'
"""
__author__ = "Jonathan Harris"
__email__ = "Jonathan Harris, Jonathan Harris <x-plane:marginal*org*uk>"
__url__ = "XPlane2Blender, http://marginal.org.uk/x-planescenery/"
__version__ = "3.11"
__bpydoc__ = """\
This script manages X-Plane cockpit panel regions,
"""

#
# Copyright (c) 2007 Jonathan Harris
#
# This code is licensed under version 2 of the GNU General Public License.
# http://www.gnu.org/licenses/gpl-2.0.html
#
# See ReadMe-XPlane2Blender.html for usage.
#

from Blender import Draw, Image, Window
from math import log

from XPlaneUtils import PanelRegionHandler

image=Image.GetCurrent()	# may be None
h=PanelRegionHandler()

opts=[]
if not image:
    pass
elif h.isRegion(image):
    opts.append('Delete this region%x1')
    opts.append('Reload all regions%x3')
elif h.isPanel(image):
    if h.countRegions()<PanelRegionHandler.REGIONCOUNT:
        opts.append('Create new region...%x2')
    else:
        opts.append('Can\'t create new region - already using maximum of %d regions%%x0' % PanelRegionHandler.REGIONCOUNT)
    opts.append('Reload all regions%x3')
elif image and 'panel.' in image.name.lower() and '.region' not in image.name.lower():
    opts.append('Create new region...%x2')

if not opts:
    r=Draw.PupMenu('This is not a Panel Texture or Region%t')
else:
    r=Draw.PupMenu('X-Plane panel regions%t|'+('|'.join(opts)))
    if r==1:
        h.delRegion(image)
        h.panelimage().makeCurrent()
    elif r==2:
        maxx=2**int(log(image.size[0],2))
        maxy=2**int(log(image.size[1],2))
        xoff=Draw.Create(0)
        yoff=Draw.Create(0)
        width=Draw.Create(min(maxx,1024))
        height=Draw.Create(min(maxy,1024))
        block=[]
        block.append(('Left:',   xoff,   0, image.size[0]))
        block.append(('Bottom:', yoff,   0, image.size[1]))
        block.append(('Width:',  width,  0, maxx))
        block.append(('Height:', height, 0, maxy))

        while Draw.PupBlock('Create new region', block):
            if not width.val or not height.val or 2**int(log(width.val,2))!=width.val or 2**int(log(height.val,2))!=height.val:
                if isinstance(block[-1], tuple): block.extend(['',''])
                block[-2]='Width & Height must'
                block[-1]='be powers of 2'
            elif xoff.val+width.val>image.size[0]:
                if isinstance(block[-1], tuple): block.extend(['',''])
                block[-2]='Left + Width must'
                block[-1]='be less than %d' % image.size[0]
            elif yoff.val+height.val>image.size[1]:
                if isinstance(block[-1], tuple): block.extend(['',''])
                block[-2]='Bottom + Height must'
                block[-1]='be less than %d' % image.size[1]
            else:
                Window.WaitCursor(1)
                if not h.isPanel(image):
                    h=h.New(image)
                h.addRegion(xoff.val, yoff.val, width.val, height.val).makeCurrent()
                Window.WaitCursor(0)
                break
    elif r==3:
        h.regenerate()
