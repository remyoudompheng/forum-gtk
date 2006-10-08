#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

# Profileur et debug
import cProfile, os, pdb, main
cProfile.run("main.main()",
        os.path.expanduser("~/tmp/forum-gtk.%s.prof" % os.getpid()))
