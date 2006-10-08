# -*- coding: utf-8 -*-

# Flrn-gtk: méthodes d'affichages d'arbres
# Rémy Oudompheng, Noël 2005

# Consts du TreeBuffer
COLWIDTH = 15. # Taille des générations
WIDTH = 8.     # Taille des nœuds
XWIDTH = 10.   # Taille du nœud courant

INDEX_SIZE = 0
INDEX_PATH = 1
INDEX_STATE = 2
INDEX_X = 3
INDEX_Y = 4
INDEX_SUBS = 5

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango
import cairo

import math

class TreeBuffer:
    """Affiche une représentation de l'arborescence du thread"""
    HEIGHT = 4000
    WIDTH = 1200

    def expose_event(self, widget, event):
        x, y, width, height = event.area
        ctx = widget.window.cairo_create()
        ctx.rectangle(x, y, width, height)
        ctx.clip()
        ctx.set_source_surface(self.surface)
        ctx.paint()
        return False

    def make_tree(self, model, root):
        """Enregistre un arbre au format 
        [n_children, 
         path, 
         state,      (non lu: 0, lu: 1, courant: 2)
         x, y, 
         [child1, child2, ...]]"""
        def iterate(iter):
            children = []
            for k in xrange(model.iter_n_children(iter)):
                children.append(iterate(model.iter_nth_child(iter, k)))
            if model.get_value(iter, 5):
                state = 1
            else: 
                state = 0
            if(model.get_path(iter) ==
               model.get_path(self.parent.summary_tab.current_node)):
                state = 2
            return [sum([c[0] for c in children]), 
                    model.get_path(iter),
                    state,
                    None, None,
                    children]

        def position(tree, gen, filled, spec_fill=False):
            """Itère sur l'arbre (on commence = gen=1 et filled=[0, 0])
            filled détermine la hauteur maximale 
                où on peut dessiner pour une génération donnée
            gen est la génération"""
            # On stockera dans height les différentes hauteurs des sous-arbres
            height = []
            width = gen * COLWIDTH
            altitude = 0
            x = width - COLWIDTH/2
            if len(filled) <= gen:
                filled.append(filled[-1])

            for k, child in enumerate(tree[INDEX_SUBS]):
                if k == 0:
                    h, w, alt = position(child, gen + 1, filled, 
                        max(filled[gen], spec_fill) - 
                        (len(tree[INDEX_SUBS]) - 1)/ 2 * COLWIDTH)
                else:
                    h, w, alt = position(child, gen + 1, filled)
                if w > width: width = w
                if alt > altitude: altitude = alt
                height.append(h)
            if len(height) == 0:
                height.append(max(filled[gen], filled[gen - 1], spec_fill)
                              + COLWIDTH/2)
            center = (height[0] + height[-1])/2
            altitude = max(altitude, center + COLWIDTH/2)

            tree[INDEX_X] = x
            tree[INDEX_Y] = center
            if tree[INDEX_STATE] == 2:
                self.currentpath = tree[INDEX_PATH]
            
            self.dots[tree[INDEX_PATH]] = (x, center)
            if filled[gen] < height[-1] + COLWIDTH/2:
                filled[gen] = height[-1] + COLWIDTH/2
            return center, width, altitude

        try: 
            del self.dots
        except: pass
        self.dots = {}        
        self.tree = iterate(root)
        c, w, a = position(self.tree, 1, [0, 0])
        self.width = w
        self.height = a

    def draw_branch(self, ctx, x0, y0, x1, y1):
        ctx.move_to(x1, y1)
        if y1 < y0 - 1.5 * COLWIDTH:
            ctx.rel_line_to(-COLWIDTH/2, 0)
            ctx.rel_curve_to(-COLWIDTH/4, 0,          # Control 1
                             -COLWIDTH/2, COLWIDTH/2, # Control 2
                             -COLWIDTH/2, 1.5 * COLWIDTH) # Destination
            ctx.line_to(x0, y0)
        elif y1 < y0 + 1.5 * COLWIDTH:
            ctx.curve_to((x0 + x1) / 2, y1,          # Control 1
                         x0, (y1 + y0)/2, # Control 2
                         x0, y0) # Destination
        else:
            ctx.rel_line_to(-COLWIDTH/2, 0)
            ctx.rel_curve_to(-COLWIDTH/4, 0,          # Control 1
                             -COLWIDTH/2, -COLWIDTH/2, # Control 2
                             -COLWIDTH/2, -1.5 * COLWIDTH) # Destination
            ctx.line_to(x0, y0)
        ctx.stroke()

    def draw_tree(self):
        """Affichage en un bloc"""
        def branches(tree):
            """Dessine les branches"""
            x, y = tree[INDEX_X], tree[INDEX_Y]
            for child in tree[INDEX_SUBS]:
                branches(child)
                self.cairo.set_source_rgb(0., 0., 0.)
                self.draw_branch(self.cairo, x, y,
                                 child[INDEX_X], child[INDEX_Y])
        def nodes(tree):
            """Dessine les nœuds"""
            x, y = tree[INDEX_X], tree[INDEX_Y]
            if tree[INDEX_STATE] == 2:
                # Nœud courant
                current_path = tree[INDEX_PATH]
                self.cairo.move_to(x, y - XWIDTH/2)
                self.cairo.rel_line_to(-XWIDTH/2, XWIDTH/2)
                self.cairo.rel_line_to(XWIDTH/2, XWIDTH/2)
                self.cairo.rel_line_to(XWIDTH/2, -XWIDTH/2)
                self.cairo.close_path()
                self.cairo.set_source_rgb(0.5, 0.5, 0.5)
                self.cairo.fill_preserve()
                self.cairo.set_source_rgb(1., 0., 0.)
                self.cairo.stroke()
            elif tree[INDEX_STATE] == 1:
                # Lu
                self.cairo.rectangle(x - WIDTH/2, y - WIDTH/2,
                                     WIDTH, WIDTH)
                self.cairo.set_source_rgb(.5, .5, .5)
                self.cairo.fill_preserve()
                self.cairo.set_source_rgb(0., 0., 0.)
                self.cairo.stroke()
            else: # Non lu
                self.cairo.arc(x, y, WIDTH/2, 0, math.pi * 2)
                self.cairo.set_line_width(2)
                self.cairo.set_source_rgb(1., 1., 1.)
                self.cairo.fill_preserve()
                self.cairo.set_line_width(1)
                self.cairo.set_source_rgb(0., 0., 0.)
                self.cairo.stroke()
            for child in tree[INDEX_SUBS]:
                nodes(child)

        # Initialisation de Cairo
        del self.surface
        self.surface = cairo.ImageSurface(
            cairo.FORMAT_RGB24, self.width, self.height)
        del self.cairo
        self.cairo = cairo.Context(self.surface)
        # Fond
        bg = self.widget.get_style().bg[0]
        self.cairo.set_source_rgb(bg.red/65536.,
                                  bg.green/65536., bg.blue/65536.)
        self.cairo.rectangle(0, 0, self.width, self.height)
        self.cairo.fill()
        self.cairo.set_line_width(1)
        # Dessin
        branches(self.tree); nodes(self.tree)
        # Affichage
        self.surface.flush()
        self.widget.set_size_request(int(self.width), int(self.height))
        self.widget.queue_draw()

        # Défilement
        x,  y = self.dots[self.currentpath]
        xadj = self.container.get_hadjustment()
        xadj.set_property("value", min(max(0, x - xadj.page_size / 2), 
                                       xadj.upper - xadj.page_size))
        self.container.set_hadjustment(xadj)
        yadj = self.container.get_vadjustment()
        yadj.set_property("value", min(max(0, y - yadj.page_size / 2),
                                       yadj.upper - yadj.page_size))
        self.container.set_vadjustment(yadj)
        return (x, y)

    def click_event(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS :
            position = (int(event.x), int(event.y))
            path = None
            for dot in self.dots:
                if ((abs(position[0] - self.dots[dot][0]) < XWIDTH/2) 
                    and (abs(position[1] - self.dots[dot][1]) < XWIDTH / 2)):
                    path = dot
                    break
            if not(path): return False
            tab = self.parent.summary_tab
            if event.button == 1:
                # Clic gauche : on sélectionne l'article
                tab.widget.get_selection().select_iter(
                    tab.data.get_iter(path))
            elif event.button == 3:
                # clic droit, on ouvre un menu contextuel
                tab.popped_article = tab.data.get_iter(path)
                tab.popup_menushow(True, event)
            return True
        return False
        
    def __init__(self, parent, pack_function):
        self.parent = parent
        self.container = gtk.ScrolledWindow()
        pack_function(self.container)
        self.container.show()

        self.tree = (0, (0,), [])

        # Création de la zone de dessin
        self.widget = gtk.DrawingArea()
        self.container.add_with_viewport(self.widget)
        self.widget.connect("expose-event", self.expose_event)
        self.widget.connect("button_press_event", self.click_event)
        self.widget.set_events(gtk.gdk.EXPOSURE_MASK |
                               gtk.gdk.LEAVE_NOTIFY_MASK |
                               gtk.gdk.BUTTON_PRESS_MASK)
        self.widget.realize()
        self.widget.show()

        self.width = 0
        self.height = 0
        self.surface = cairo.ImageSurface(
            cairo.FORMAT_RGB24, self.width, self.height)
        self.cairo = None
        self.dots = {}
