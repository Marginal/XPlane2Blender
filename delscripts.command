#!/bin/bash

clear
echo

FOO=~/.blender/scripts

if [ -e "$FOO" ]; then
    rm -rf "$FOO"
    if [ -e "$FOO" ]; then
        echo "Couldn't delete ~/.blender/scripts folder !!!";
    else
        echo "Deleted ~/.blender/scripts folder.";
    fi;
else
    echo "~/.blender/scripts doesn't exist.";
fi
