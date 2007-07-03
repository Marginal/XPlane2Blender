#!/bin/bash

if [ -e "$HOME/.blender/scripts" ]; then
    echo "Deleted scripts folder"
    rm -rf "$HOME/.blender/scripts";
else
    echo "Didn't find scripts folder";
fi
