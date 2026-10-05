#!/bin/sh
# Offline developer rebuild from the corresponding-source ZIP. Never an installer.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/jxrlib"
test "$(uname -s)" = Darwin
test "$(uname -m)" = arm64
: "${JAVA_HOME:?Set JAVA_HOME to an existing native ARM JDK with JNI headers}"
test -f "$JAVA_HOME/include/jni.h"
# Generated sources are included so an ordinary native rebuild needs no SWIG.
# To regenerate, explicitly request it and use the recorded SWIG 4.5.0 tool.
if [ "${1:-}" = --regenerate ]; then
    : "${SWIG:=swig}"
    "$SWIG" -version
    "$SWIG" -version | grep 'SWIG Version 4.5.0' >/dev/null
    make swig "SWIG=$SWIG -I$(pwd)/gat-legacy-swig"
fi
export JAVA_HOME
export MACOSX_DEPLOYMENT_TARGET=11.0
make -j2 "$(pwd)/build/libjxrjava.dylib" \
  'CC=clang -arch arm64 -mmacosx-version-min=11.0 -include gat-compat.h -Wno-error=incompatible-pointer-types' \
  'CXX=clang++ -arch arm64 -mmacosx-version-min=11.0 -std=c++98'
file build/libjxrjava.dylib
lipo -info build/libjxrjava.dylib
otool -L build/libjxrjava.dylib
shasum -a 256 build/libjxrjava.dylib
