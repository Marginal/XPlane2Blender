#!/bin/sh
# Installation script for OSX & Linux
clear
echo Installing Blender scripts . . .
echo

cd `dirname $0`
DESTDIR=$HOME/.blender/scripts

# Remove old versions
FILES="../Bpymenus helpXPlane.py uvCopyPaste.py uvResize.py XPlaneExport.py XPlaneExport.pyc XPlaneExport7.py XPlaneExport8.py XPlaneExportBodies.py XPlaneImport.py XPlaneImportPlane.py XPlaneImportBodies.py XPlaneUtils.py XPlaneUtils.pyc XPlaneACF.py XPlaneACF.pyc XPlane2Blender.html XPlaneImportPlane.html XPlaneReadme.txt"
for I in $FILES; do
    if [ -e "$DESTDIR/$I" ]; then rm "$DESTDIR/$I"; fi
done
 
mkdir -p "$DESTDIR"
FILES="helpXPlane.py uvCopyPaste.py uvResize.py XPlaneExport.py XPlaneExport7.py XPlaneExport8.py XPlaneImport.py XPlaneImportPlane.py XPlaneUtils.py XPlaneACF.py XPlane2Blender.html"
cp -f $FILES "$DESTDIR"
for I in $FILES; do
    if ! [ -r "$DESTDIR/$I" ]; then
	echo Failed to install scripts in $DESTDIR !!!
	echo
	exit 1;
    fi;
done

echo Installation successful.
echo
