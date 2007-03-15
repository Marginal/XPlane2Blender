#!/bin/sh
# Installation script for OSX & Linux
clear
echo Installing Blender scripts . . .

cd "`dirname "$0"`"
IFS="
"

# Candidate application locations
DIRS=$(/System/Library/Frameworks/ApplicationServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | awk 'match($0, "blender.app") {if(sub("[ \t]+path:[ \t]+","")) print $0 "/Contents/MacOS/.blender/scripts"}')

# Remove old files from everywhere
FILES="../Bpymenus
helpXPlane.py
uvCopyPaste.py
uvResize.py
XPlaneExport.py
XPlaneExport.pyc
XPlaneExport7.py
XPlaneExport8.py
XPlaneExportBodies.py
XPlaneImport.py
XPlaneImportPlane.py
XPlaneImportBodies.py
XPlaneUtils.py
XPlaneUtils.pyc
XPlaneACF.py
XPlaneACF.pyc
XPlane2Blender.html
XPlaneImportPlane.html
XPlaneReadme.txt"
for I in "$HOME/.blender/scripts" $DIRS; do
    for J in $FILES; do
        if [ -e "$I/$J" ]; then
	    rm "$I/$J";
	fi
    done;
done

# Files to install
FILES="helpXPlane.py
uvCopyPaste.py
uvResize.py
XPlaneExport.py
XPlaneExport7.py
XPlaneExport8.py
XPlaneImport.py
XPlaneImportPlane.py
XPlaneUtils.py
XPlaneACF.py
XPlane2Blender.html"
if [ -d "$HOME/.blender/scripts" ]; then
    DIRS="$HOME/.blender/scripts"
fi

# Copy new
DONE=
for I in $DIRS; do
    if [ -d $I ]; then
	DONE="$DONE
$I"
	cp -f $FILES $I
	for J in $FILES; do
	    if ! [ -r $I/$J ]; then
		echo
		echo Failed to install scripts in folder
		echo "  $I" !!!
		echo
		exit 1;
	    fi;
	done
    fi;
done

echo
if [ "$DONE" ]; then
    echo "Installated scripts in folder:"
    echo "  $DONE"
else
    echo Failed to find the correct location for the scripts !!!
fi
echo
