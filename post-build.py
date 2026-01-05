#!/usr/bin/python3

import glob
import shutil

for f in glob.glob("public/*/*/*/*/index.html"):
    shutil.copy(f, f.replace('/index.html', '.html'))
