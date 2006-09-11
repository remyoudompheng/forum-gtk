# -*- coding: utf-8 -*-

# Flrn-gtk: panneau des groupes
# Rémy Oudompheng, Noël 2005-Septembre 2006

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

# Modules Python
import time
import os, sys

# Constantes
GRP_COLUMN_NAME = 0
GRP_COLUMN_CAPTION = 1
GRP_COLUMN_SUBSCRIBED = 2
GRP_COLUMN_ISREAL = 3

# Panneau d'affichage de groups
class GroupBuffer:
    # Affichage du panneau Groupes
    def format_group_name(self, text, prefix=""):
        return text.replace(
            self.parent.conf.params['prefixe_groupe'], '', 1)
        for i in xrange(len(comps[:-1])):
            comps[i] = comps[i][:1]
        return prefix + '.'.join(comps)

    def display_tree(self, list):
        """construit un arbre directement à partir de la liste (nom, data)"""
        def format_node(item, depth):
            "Formate tout bien"
            # Selon qu'on est dans la liste des groupes, ou pas
#PYTHON2.5 MIGRATION
            if item[1]['arts']:
                caption = item[1]['arts'] + ':'
                if int(item[1]['arts']) > 0:
                    font = "monospace bold"
                else:
                    font = "monospace italic"
            else:
                caption = ""
                font = "monospace"
            # Le reste
            if self.parent.conf.params['abbr_group_names']:
                caption += ".".join([s[:1] for s in item[0][:depth - 1]])
            else:
                caption += ".".join(item[0][:depth - 1])
            if depth == 1:
                caption += ".".join(item[0][depth - 1:])
            else: caption += "." + ".".join(item[0][depth - 1:])
                        
#            caption = (item[1]['arts'] + ':' if item[1]['arts'] else '')
#            font = 'monospace' + (
#                '' if not item[1]['arts'] else (
#                ' bold' if int(item[1]['arts']) > 0 else ' italic'))
#
#            # Le reste
#            if self.parent.conf.params['abbr_group_names']:
#                caption += ".".join([s[:1] for s in item[0][:depth - 1]])
#            else:
#                caption += ".".join(item[0][:depth - 1])
#            caption += ("." if depth > 1 else "") + \
#                       ".".join(item[0][depth - 1:])
#END MIGRATION

            return [item[1]['name'], caption, item[1]['subd'], True, font]

        def grow_tree(root, list, depth):
            """Construit une branche à partir d'une racine root, d'une
            liste de groupes list à une profondeur depth"""
            if len(list) == 1:
                self.group2node[list[0][1]['name']] = self.data.append(
                    root, format_node(list[0], depth))
                return
            subtrees = {}
            ordered_subtrees = []
            # Si jamais la hiérarchie correspond à un nœud
            node = None
            newroot = root
            for l in list:
                if len(l[0]) == depth:
                    # On a trouvé le nœud racine
                    node = l
                    continue
                # On regarde l'enbranchement et on le crée si nécessaire
                if l[0][depth] not in subtrees:
                    subtrees[l[0][depth]] = []
                    ordered_subtrees.append(l[0][depth])
                subtrees[l[0][depth]].append(l)
            if node:
                # Il y a un vrai groupe, on le met
                newroot = self.data.append(root, format_node(node, depth))
                self.group2node[node[1]['name']] = newroot
            elif (len(subtrees) > 1) and (depth > 0):
                # Il y a différentes branches, on crée un noeud bouche-trou
                newroot = self.data.append(
                    root, ["", ".".join(list[0][0][:depth]),
                           False, False, "normal"])
            for b in ordered_subtrees:
                grow_tree(newroot, subtrees[b], depth + 1)

        self.data.clear()
        try:
            del self.group2node
            self.group2node = {}
        except AttributeError:
            self.group2node = {}
        if len(list):
            grow_tree(None, list, 0)
        self.widget.set_model(self.data)
        self.widget.expand_all()

    def refresh_tree(self, all_groups = False):
        if not(all_groups):
            arts = self.parent.conf.unreads
#PYTHON2.5 MIGRATION
        digits = 0
        if len(arts):
            digits = len(str(max(arts.values())))
#            digits = (len(str(max(arts.values())))
#                      if len(arts) else 0)
# END MIGRATION
            self.display_tree(
                [[g.replace(
                self.parent.conf.params['prefixe_groupe'],"", 1).split('.'), 
                  {'name': g,
                   'subd': True,
                   'arts': str(arts[g]).rjust(digits)}]
                 for g in sorted(self.parent.conf.subscribed)])
            return arts
        else:
            self.display_tree(
                [[g.replace(
                self.parent.conf.params['prefixe_groupe'],"", 1).split('.'), 
                  {'name': g,
                   'subd': g in self.parent.conf.subscribed,
                   'arts': None}]
                 for g in sorted(self.parent.conf.groups)])

    def toggle_callback(self, widget, path, data=None):
        """Cochage de case"""
        self.data.set_value(
            self.data.get_iter(path), 2,
            not(self.data.get_value(self.data.get_iter(path), 2)))
        
    def click_callback(self, widget, event):
        if (event.type == gtk.gdk.BUTTON_PRESS) and event.button == 3:
            position = widget.get_path_at_pos(int(event.x), int(event.y))
            if not(position):
                return False
            row = self.data[position[0]]
            # On vérifie que c'est un vrai groupe
            if self.data.get_value(row.iter, GRP_COLUMN_ISREAL):
                self.popped_group = self.data.get_value(row.iter, GRP_COLUMN_NAME)
                self.popup_menushow(True, event)
                return True
        return False

    def popup_menushow(self, clicked, event=None):
        if not(clicked):
            path = self.widget.get_cursor()[0]
            if path and self.data.get_value(path, GRP_COLUMN_ISREAL):
                # On vérifie que c'est un vrai groupe
                self.popped_group = self.data.get_value(path, GRP_COLUMN_NAME)
            else: 
                return False
        # On affiche le menu
        popup_menu = self.ui_manager.get_widget("/ui/ContextMenu")
        popup_menu.set_title = self.popped_group
        popup_menu.show_all()
        if clicked: 
            popup_menu.popup(None, None, None, event.button, event.time)
        else:
            popup_menu.popup(None, None, None, None, None)

    # Actions du menu contextuel
    def popup_unsubscribe(self, action):
        self.parent.conf.subscribed.remove(self.popped_group)
        self.parent.conf.unsubscribed.add(self.popped_group)
        self.refresh_tree(False)
        return True

    def popup_gotoart(self, action):
        self.widget.get_selection().select_iter(self.group2node[self.popped_group])
        self.parent.action_sumgoto_callback(None)
        return True

    def popup_gotosum(self, action):
        self.widget.get_selection().select_iter(self.group2node[self.popped_group])
        self.parent.action_overview_callback(None)
        return True

    def popup_killarts(self, action):
        read_list = self.parent.conf.groups[self.popped_group]
        vals = self.parent.conf.server.group_stats(self.popped_group)
        if vals:
            # Préparation de la boîte de dialogue
            dialog = gtk.Dialog(u"Voir le sommaire du groupe",
                                self.parent.window, gtk.DIALOG_MODAL,
                                (gtk.STOCK_OK, gtk.RESPONSE_OK))
            step = int((vals[1] - vals[0]) / 5000) * 100 + 100
            start_entry = gtk.SpinButton(
                gtk.Adjustment(vals[0], vals[0], vals[1], 1, step))
            end_entry = gtk.SpinButton(
                gtk.Adjustment(vals[1], vals[0], vals[1], 1, step))
            hbox = gtk.HBox()
            hbox.pack_start(gtk.Label(u"Marquer comme lus les numéros "),
                            False, False, 0)
            hbox.pack_start(start_entry, True, True, 0)
            hbox.pack_start(gtk.Label(u" à "), False, False, 0)
            hbox.pack_start(end_entry, True, True, 0)
            
            dialog.vbox.pack_start(
                gtk.Label(u"Groupe : " + self.popped_group),
                False, False, 0)
            dialog.vbox.pack_start(hbox, True, True, 0)
            dialog.vbox.show_all()
            
            # Récupération de la réponse
            tagged_range = [1, 1]
            def get_user_entry(widget, resp_id, data):
                if resp_id == gtk.RESPONSE_OK:
                    data[0] = start_entry.get_value_as_int()
                    data[1] = end_entry.get_value_as_int()
                    return None
            dialog.connect("response", get_user_entry, tagged_range)
                
            if dialog.run() == gtk.RESPONSE_OK:
                read_list.add_range(tagged_range)
            dialog.destroy()
            self.refresh_tree()

    def popup_unkillarts(self, action):
        read_list = self.parent.conf.groups[self.popped_group]
        vals = self.parent.conf.server.group_stats(self.popped_group)
        if vals:
            # Préparation de la boîte de dialogue
            dialog = gtk.Dialog(u"Voir le sommaire du groupe",
                                self.parent.window, gtk.DIALOG_MODAL,
                                (gtk.STOCK_OK, gtk.RESPONSE_OK))
            step = int((vals[1] - vals[0]) / 5000) * 100 + 100
            start_entry = gtk.SpinButton(
                gtk.Adjustment(vals[0], vals[0], vals[1], 1, step))
            end_entry = gtk.SpinButton(
                gtk.Adjustment(vals[1], vals[0], vals[1], 1, step))
            hbox = gtk.HBox()
            hbox.pack_start(gtk.Label(u"Marquer comme non lus les numéros "),
                            False, False, 0)
            hbox.pack_start(start_entry, True, True, 0)
            hbox.pack_start(gtk.Label(u" à "), False, False, 0)
            hbox.pack_start(end_entry, True, True, 0)
            
            dialog.vbox.pack_start(
                gtk.Label(u"Groupe : " + self.popped_group),
                False, False, 0)
            dialog.vbox.pack_start(hbox, True, True, 0)
            dialog.vbox.show_all()
            
            # Récupération de la réponse
            tagged_range = [1, 1]
            def get_user_entry(widget, resp_id, data):
                if resp_id == gtk.RESPONSE_OK:
                    data[0] = start_entry.get_value_as_int()
                    data[1] = end_entry.get_value_as_int()
                    return None
            dialog.connect("response", get_user_entry, tagged_range)
                
            if dialog.run() == gtk.RESPONSE_OK:
                read_list.del_range(tagged_range)
            dialog.destroy()
            self.refresh_tree()

    def __init__(self, parent, pack_function, show_subscriptions = False):
        self.parent = parent
        self.subcriptions = show_subscriptions
        # Panneau à contis
        self.data = gtk.TreeStore(
            gobject.TYPE_STRING,  # Nom
            gobject.TYPE_STRING,  # Caption
            gobject.TYPE_BOOLEAN, # Abonné ?
            gobject.TYPE_BOOLEAN, # Est un vrai ?
            gobject.TYPE_STRING)  # Police

        self.container = gtk.ScrolledWindow()
        self.container.set_policy(gtk.POLICY_AUTOMATIC,
                                  gtk.POLICY_AUTOMATIC)
        pack_function(self.container)
        self.container.show()

        self.widget = gtk.TreeView(self.data)
        self.container.add(self.widget)
        self.widget.show()

        # Colonne du nom
        self.column_name = gtk.TreeViewColumn(
            'Conti',gtk.CellRendererText(), text=1, font=4)
        self.column_name.set_resizable(True)
        self.widget.append_column(self.column_name)
        if show_subscriptions:
            # Colonne des abonnements
            toggling_cell_renderer = gtk.CellRendererToggle()
            toggling_cell_renderer.connect("toggled", self.toggle_callback)
            self.column_subscr = gtk.TreeViewColumn(
                u'Abonné', toggling_cell_renderer, active=2, activatable=3, visible=3)
            self.column_subscr.set_resizable(False)
            self.widget.append_column(self.column_subscr)
        self.widget.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.widget.set_property("expander-column", self.column_name)

        # Et maintenant, un menu contextuel
        if not(show_subscriptions):
            menu_xmldef = """
            <ui>
            <popup name="ContextMenu" action="PopupMenuAction">
            <menuitem name="Unsubscribe" action="UnsubscribeAction"/>
            <menuitem name="GotoSummary" action="GotoSummaryAction"/>
            <menuitem name="GotoArticle" action="GotoArticleAction"/>
            <menuitem name="KillArts" action="KillArtsAction"/>
            <menuitem name="UnkillArts" action="UnkillArtsAction"/>
            </popup>
            </ui>"""
            self.ui_manager = gtk.UIManager()
            self.ui_manager.add_ui_from_string(menu_xmldef)
            self.action_group = gtk.ActionGroup("PopupMenuActions")
            self.action_group.add_actions([
                    ("PopupMenuAction", None, "", None, None, None),
                    ("UnsubscribeAction", None, u"Se _désabonner", None, 
                     u"Se désabonner du groupe", self.popup_unsubscribe),
                    ("GotoSummaryAction", None, u"Voir le _sommaire...", None,
                     u"Afficher le sommaire du groupe", self.popup_gotosum),
                    ("GotoArticleAction", None, u"Voir l'_article numéro...", None,
                     u"Afficher l'article portant le numéro indiqué",
                     self.popup_gotoart),
                    ("KillArtsAction", None, u"Marquer comme lu...", None,
                     u"Marque les articles indiqués comme lus",
                     self.popup_killarts),
                    ("UnkillArtsAction", None, u"Marquer comme non-lu...", None,
                     u"Marque les articles indiqués comme non lus",
                     self.popup_unkillarts)])
            self.ui_manager.insert_action_group(self.action_group, 0)
            self.widget.connect("button-press-event", self.click_callback)
            self.widget.connect("popup-menu", self.popup_menushow, False)