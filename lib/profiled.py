#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

# Profileur et debug
import hotshot.stats, pdb, main
prof = hotshot.stats.Profile()
prof.runcall(main.main)
prof.create_stats()
prof.print_stats(sort="cumulative")

