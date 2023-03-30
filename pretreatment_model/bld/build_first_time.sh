#!/bin/bash

make clean
make
make ptpython
cp *.exe ../test/
cp *.so ../test/

