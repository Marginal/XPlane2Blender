#!/bin/bash
# Installation script for MacOS X
clear
echo Installing Blender scripts . . .

cd "`dirname "$0"`"
IFS="
"

# Find lsregister
if [ -x /System/Library/Frameworks/ApplicationServices.framework/Frameworks/LaunchServices.framework/Support/lsregister ] ;then
    LS=/System/Library/Frameworks/ApplicationServices.framework/Frameworks/LaunchServices.framework/Support/lsregister;
elif [ -x /System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister ] ; then
    # From http://developer.apple.com/documentation/Carbon/Conceptual/MDImporters/Concepts/Troubleshooting.html
    LS=/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister;
else
    echo Can\'t find the lsregister tool!
    LS=echo;
fi

# Candidate application locations
DIRS=$($LS -dump | awk 'match($2, "/[B|b]lender.app") { print $2 "/Contents/MacOS/.blender/scripts"}')

# Remove old files from everywhere
FILES="../Bpymenus
helpXPlane.py
uvCopyPaste.py
uvFixupACF.py
uvResize.py
XPlaneExport.py
XPlaneExport.pyc
XPlaneExport7.py
XPlaneExport8.py
XPlaneExportCSL.py
XPlaneExportBodies.py
XPlaneImport.py
XPlaneImport.pyc
XPlaneImportPlane.py
XPlaneImportBodies.py
XPlaneUtils.py
XPlaneUtils.pyc
XPlaneACF.py
XPlaneACF.pyc
XPlane2Blender.html
XPlaneImportPlane.html
XPlaneReadme.txt
DataRefs.txt"

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
uvFixupACF.py
uvResize.py
XPlaneExport.py
XPlaneExport7.py
XPlaneExport8.py
XPlaneExportCSL.py
XPlaneImport.py
XPlaneImportPlane.py
XPlaneUtils.py
XPlane2Blender.html
DataRefs.txt"
if [ -d "$HOME/.blender/scripts" ]; then
    DIRS="$HOME/.blender/scripts"
fi

# Copy new
DONE=
for I in $DIRS; do
    if [ -d "$I" ]; then
	DONE="$DONE
  $I"
	cp -f $FILES "$I"
	for J in $FILES; do
	    if ! [ -r "$I/$J" ]; then
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
    echo "Installed scripts in folder:"
    echo "$DONE"
else
    echo Failed to find the correct location for the scripts !!!
fi
echo
