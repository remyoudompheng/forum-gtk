# -*- coding: utf-8 -*-

# Flrn-gtk: méthode d'affichage d'arbre utilisant VPython
# Rémy Oudompheng, Noël 2005

# Consts du TreeBuffer
COLWIDTH = 15 # Taille des générations
WIDTH = 5     # Taille des nœuds
XWIDTH = 7   # Taille du nœud courant
LINEWIDTH = 1.5   # Époisseur des lignes

INDEX_SIZE = 0
INDEX_PATH = 1
INDEX_STATE = 2
INDEX_SUBS = 3

import visual

class GLTreeBuffer:
    """Affiche une représentation de l'arborescence du thread"""
    def make_tree(self, model, root):
        """Enregistre un arbre au format 
        (n_children, 
         state,      (non lu: 0, lu: 1, courant: 2)
         path, 
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
        def iterate(tree, gen, filled, spec_fill=0):
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
                        tree[INDEX_SUBS][k], gen + 1, filled,
                        max(filled[gen], spec_fill) - 
                        (len(tree[INDEX_SUBS]) - 1)/ 2 * COLWIDTH)
                else:
                    h, w, alt, new_path = iterate(
                        tree[INDEX_SUBS][k], gen + 1, filled)
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
            for k in xrange(len(tree[INDEX_SUBS])):
                visual.curve(pos=[(center, -x, 0),
                           (height[k], - x - COLWIDTH, 0)], radius=LINEWIDTH)

            # Le nœud
            point = (center, -x, 0)
            if tree[INDEX_STATE] == 2:
                current_path = tree[INDEX_PATH]
                # Le nœud courant est vert
                visual.sphere(pos=point,
                       radius=WIDTH,
                       color=(0.0, 1.0, 0.0))
            elif tree[INDEX_STATE] == 1:
                # Si c'est lu, on met en rouge
                visual.sphere(pos=point,
                       radius=WIDTH,
                       color=(0.5, 0.0, 0.0))
            else: 
                # Sinon, on met en rouge clair
                visual.sphere(pos=point,
                       radius=WIDTH,
                       color=(1.0, 0.3, 0.3))
                
            self.dots[tree[INDEX_PATH]] = point
            if filled[gen] < height[-1] + COLWIDTH/2:
                filled[gen] = height[-1] + COLWIDTH/2
            return center, width, altitude, current_path

        try: 
            del self.dots
        except AttributeError: pass
        self.dots = {}
        
        try:
            for i in self.window.objects: i.visible = 0
        except AttributeError:
            self.window = visual.display(
                title='Alpha-tree', width=300, height=200,
                background=(1.0, 1.0, 1.0))
            self.window.visible = 1
            self.window.uniform = 1
            self.window.autoscale = 0
            self.window.range = (90, 90, 90)
        h, w, z, path = iterate(self.tree, 1, [0, 0])
        try: coords = self.dots[path]
        except: print path
        self.window.center = coords
        return coords
    
    def __init__(self, parent):
        self.parent = parent
        self.tree = (0, (0,), [])
        self.dots = {}


