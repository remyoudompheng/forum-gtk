#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

import cProfile, pstats, pstatscalltree
import main, os, pdb

home = os.getenv("HOME")

bidule = cProfile.Profile()
bidule.run("main.main()")

# Sortie KCacheGrind
merger = pstats.Stats(bidule)
try:
    merger.add("/tmp/forum-gtk.prof")
except:
    pass
merger.dump_stats("/tmp/forum-gtk.prof")

analyser = pstatscalltree.KCacheGrind(merger)
file = open("/tmp/forum-gtk.kprof", "w+")
analyser.output(file)
file.close()
