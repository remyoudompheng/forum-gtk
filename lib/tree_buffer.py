# -*- coding: utf-8 -*-

# Flrn-gtk: méthodes d'affichages d'arbres
# Rémy Oudompheng, Noël 2005

# Consts du TreeBuffer
COLWIDTH = 15 # Taille des générations
WIDTH = 8    # Taille des nœuds
XWIDTH = 10   # Taille du nœud courant

INDEX_SIZE = 0
INDEX_PATH = 1
INDEX_STATE = 2
INDEX_SUBS = 3

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

class TreeBuffer:
    """Affiche une représentation de l'arborescence du thread"""
    HEIGHT = 4000
    WIDTH = 1200

    def expose_event(self, widget, event):
        x, y, width, height = event.area
        gc = widget.get_style().fg_gc[gtk.STATE_NORMAL]
        widget.window.clear()
        widget.window.draw_drawable(gc, self.pixmap, x, y, x, y, width, height)
        return False

    def make_tree(self, model, root):
        """Enregistre un arbre au format 
        (n_children, 
         path, 
         state,      (non lu: 0, lu: 1, courant: 2)
         [child1, child2, ...])"""
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
            return (sum([c[0] for c in children]), 
                    model.get_path(iter),
                    state,
                    children)
        self.tree = iterate(root)

    def draw_tree(self):
        """Affichage en un bloc"""
        def iterate(tree, gen, filled, drawable, style, spec_fill=0):
            """Itère sur l'arbre (on commence = gen=1 et filled=[0, 0])
            filled détermine la hauteur maximale 
                où on peut dessiner pour une génération donnée
            gen est la génération"""
            # On stockera dans height les différentes hauteurs des sous-arbres
            height = []
            width = gen * COLWIDTH
            altitude = 0
            current_path = None
            x = width - COLWIDTH/2
            if len(filled) <= gen:
                filled.append(filled[-1])

            for k in xrange(len(tree[INDEX_SUBS])):
                if k == 0:
                    h, w, alt, new_path = iterate(
                        tree[INDEX_SUBS][k], gen + 1, filled, drawable, style,
                        max(filled[gen], spec_fill) - 
                        (len(tree[INDEX_SUBS]) - 1)/ 2 * COLWIDTH)
                else:
                    h, w, alt, new_path = iterate(
                        tree[INDEX_SUBS][k], gen + 1, filled, drawable, style)
                if w > width: width = w
                if alt > altitude: altitude = alt
                height.append(h)
                if new_path != None: current_path = new_path
            if len(height) == 0:
                height.append(max(filled[gen], filled[gen - 1], spec_fill)
                              + COLWIDTH/2)
            center = (height[0] + height[-1])/2
            altitude = max(altitude, center + COLWIDTH/2)

            # Les traits
            drawable.draw_line(style.fg_gc[0], x - COLWIDTH/2, center, x, center)
            for k in xrange(len(tree[INDEX_SUBS])):
                z = height[k]
                if z < center - 1.5 * COLWIDTH:
                    drawable.draw_arc(style.fg_gc[0], False, x, z, 
                                     COLWIDTH, 2*COLWIDTH, 11520, -5760)
                    drawable.draw_line(style.fg_gc[0], 
                                       x, z + COLWIDTH,
                                       x, center)
                elif z < center:
                    drawable.draw_arc(style.fg_gc[0], False, x, z, 
                                     COLWIDTH, 2*(center - z), 11520, -5760)
                elif z == center:
                    drawable.draw_line(style.fg_gc[0], 
                                       x, center,
                                       x + COLWIDTH/2, center)
                elif z < center + 1.5 * COLWIDTH:
                    drawable.draw_arc(style.fg_gc[0], False, x, 2*center - z, 
                                     COLWIDTH, 2*(z - center), 11520, 5760)
                else:
                    drawable.draw_arc(style.fg_gc[0], False, 
                                      x, z - 2 * COLWIDTH, 
                                      COLWIDTH, 2*COLWIDTH, 11520, 5760)
                    drawable.draw_line(style.fg_gc[0], 
                                       x, z - COLWIDTH,
                                       x, center)
            # Le nœud
            if tree[INDEX_STATE] == 2:
                current_path = tree[INDEX_PATH]
                # Le nœud courant est creux
                cycle = ((x, center - XWIDTH/2),
                         (x - XWIDTH/2, center),
                         (x, center + XWIDTH/2),
                         (x + XWIDTH/2, center))
                drawable.draw_polygon(style.light_gc[0], True, cycle)
                drawable.draw_polygon(style.fg_gc[0], False, cycle)
            elif tree[INDEX_STATE] == 1:
                # Si c'est lu, on met un carré
                drawable.draw_rectangle(style.dark_gc[0], True,
                                        x - WIDTH/2, center - WIDTH/2,
                                        WIDTH, WIDTH)
            else: 
                # Sinon, on met un rond
                drawable.draw_arc(style.fg_gc[0], True, 
                                  x - WIDTH/2, center - WIDTH/2,
                                  WIDTH, WIDTH, 0, 23040)
            self.dots[tree[INDEX_PATH]] = (x, center)
            if filled[gen] < height[-1] + COLWIDTH/2:
                filled[gen] = height[-1] + COLWIDTH/2
            return center, width, altitude, current_path

        try: 
            del self.dots
        except: pass
        self.dots = {}
        self.pixmap.draw_rectangle(self.widget.get_style().bg_gc[0], True, 
                                   0, 0, self.WIDTH, self.HEIGHT)
        h, w, z, path = iterate(
            self.tree, 1, [0, 0], self.pixmap, self.widget.get_style())
        self.widget.set_size_request(w, z)
        self.pictsize = (w, z)
        self.widget.queue_draw()

        # Défilement
        x,  y = self.dots[path]
        xadj = self.container.get_hadjustment()
        xadj.set_property("value", min(max(0, x - xadj.page_size / 2), 
                                       xadj.upper - xadj.page_size))
        self.container.set_hadjustment(xadj)
        yadj = self.container.get_vadjustment()
        yadj.set_property("value", min(max(0, y - yadj.page_size / 2),
                                       yadj.upper - yadj.page_size))
        self.container.set_vadjustment(yadj)

        return self.dots[path]

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
        self.pictsize = (self.WIDTH, self.HEIGHT)
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
        # Nettoyage
        self.pixmap = gtk.gdk.Pixmap(self.widget.window, self.WIDTH, self.HEIGHT)
        self.pixmap.draw_rectangle(self.widget.get_style().bg_gc[0], True, 
                                   0, 0, self.WIDTH, self.HEIGHT)
        self.dots = {}
