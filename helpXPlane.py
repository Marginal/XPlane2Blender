#!BPY
"""
Name: 'X-Plane'
Blender: 236
Group: 'Help'
Tooltip: 'XPlane2Blender manual'
"""
__author__ = "Jonathan Harris"
__url__ = ("XPlane2Blender homepage, http://marginal.org.uk/x-planescenery/")
__version__ = "2.00"
__bpydoc__ = """\
This script opens the default web browser at the XPlane2Blender manual.
"""

import Blender, webbrowser
webbrowser.open("file:%s" % (Blender.sys.join(Blender.Get('scriptsdir'),
                                              'XPlane2Blender.html')))
