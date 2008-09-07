#!BPY
""" Registration info for Blender menus:
Name: 'Debug'
Blender: 234
Group: 'Export'
"""

print "Debug mode"

import rpdb2; rpdb2.start_embedded_debugger("foo", True)

from XPlaneExport8 import OBJexport
