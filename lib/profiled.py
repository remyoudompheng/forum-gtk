#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

# Profileur et debug
import hotshot, pdb, main
prof = hotshot.Profile(os.path.expanduser("~/tmp/forum-gtk.prof"))
prof.start()
main.main()
prof.close()

stat = hotshot.stats.load(os.path.expanduser('~/tmp/forum-gtk.prof'))
stat.strip_dirs()
stat.sort_stats('time', 'calls')
stat.print_stats(30)
stat.sort_stats('cumulative', 'calls')
stat.print_stats(30)

