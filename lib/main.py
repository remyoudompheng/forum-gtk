#! /usr/bin/env python2.4
# -*- coding: utf-8 -*-

# Flrn-gtk: fenêtre principale
# Rémy Oudompheng, Noël 2005

import getopt, os, sys
import flrn_config

# Profileur et debug
import hotshot, pdb
prof = hotshot.Profile(os.path.expanduser("~/src/forum-gtk/forum-gtk.prof"))
prof.start()


HELP_STRING = u"""Syntaxe: program [-ch] [-d dir] [-n name] [--opengl]
Options:
 -c                 affiche le nombre de messages non lus
 -h, --help         affiche cette aide
 -d, --conf-dir     indique le dossier contenant les fichiers de configuration
 -n, --optname name indique le groupe d'options à utiliser
 --opengl           utiliser l'arbre 3D"""
    

def main():
    # Récupération des options de la ligne de commande
    optlist, args = getopt.getopt(
        sys.argv[1:], "cd:hn:",
        ['optname=', 'conf-dir=', 'co', 'help', 'opengl'])
    optlist = dict(optlist)

    # L'aide
    if '-h' in optlist or '--help' in optlist:
        print HELP_STRING.encode(locale.getpreferredencoding())
        sys.exit(0)

    # Chargement des options
    try:
        server = optlist['--server']
    except KeyError:
        try: server = optlist['-n']
        except KeyError: server = None
    try:
        conf_dir = optlist['--conf-dir']
    except KeyError:
        try: conf_dir = optlist['-d']
        except KeyError: conf_dir = None

    conf_source = flrn_config.FlrnConfig(conf_dir, server)

    # Dénombrement des messages non lus
    unreads = 0
    if ('-c' in optlist) or ('--co' in optlist):
        conf_source.update_unreads()
        for g in conf_source.unreads:
            if conf_source.unreads[g] == 1:
                print '  ' + g + ':', '1 article non lu.'
                unreads += 1
            if conf_source.unreads[g] > 1:
                print '  ' + g + ':', \
                    conf_source.unreads[g], 'articles non lus.'
                unreads += conf_source.unreads[g]
        if unreads == 0:
            print 'Rien de nouveau.'
        elif unreads == 1:
            print 'Il y a au total 1 article non lu.'
        else:
            print 'Il y a au total', unreads, 'articles non lus.'
        sys.exit(0)

    # Est-ce l'heure ?
    if not(flrn_config.is_geek_time(
            conf_source.params['geek_start_time'],
            conf_source.params['geek_end_time'])):
        print "C'est pas l'heure de lire forum !"
        sys.exit(0)

    # Chargement de l'interface avec OpenGL ou pas
    if '--opengl' in optlist:
        import gtkgl_gui
        gui = gtkgl_gui.MainWindow(conf_source)
    else:
        import gtk_gui 
        gui = gtk_gui.MainWindow(conf_source)
        
    import gtk
    gtk.main()

if __name__ == "__main__":
    main()
    
prof.close()
