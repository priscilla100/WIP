#!/bin/bash
dune build
ln -sf _build/default/src/main.exe precis
echo "✅ Built: ./precis"