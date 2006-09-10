# -*- coding: utf-8 -*-

# Flrn-gtk: éléments de l'interface graphique
# Rémy Oudompheng, Noël 2005

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

# Modules Python
import email.Utils
import time
import os, sys
from tempfile import mkstemp
import textwrap

import re
# Regexps de coloriage
msgid_regexp = re.compile("(<[^ ><@]*@[^ ><@]*>)")
weblink_regexp = re.compile("((?:ftp|http)://[^ \n]*)")
quote1_regexp = re.compile("\n(?:>>>)*> ([^\n]*)")
quote2_regexp = re.compile("\n(?:>>>)*>> ([^\n]*)")
quote3_regexp = re.compile("\n(?:>>>)*>>> ([^\n]*)")
signature_regexp = re.compile("(\n-- \n)")

# Modules
import nntp_io
import flrn_config

# Constantes
GRP_COLUMN_NAME = 0
GRP_COLUMN_CAPTION = 1
GRP_COLUMN_SUBSCRIBED = 2
GRP_COLUMN_ISREAL = 3

SUM_COLUMN_MSGID = 0
SUM_COLUMN_NUM = 1
SUM_COLUMN_SUBJ = 2
SUM_COLUMN_FROM = 3
SUM_COLUMN_DATE = 4
SUM_COLUMN_READ = 5

# Panneau d'affichage de groups
class GroupBuffer:
    # Affichage du panneau Groupes
    def format_group_name(self, text, prefix=""):
        return text.replace(
            self.parent.conf.params['prefixe_groupe'], '', 1)
            #).replace(prefix, '').split('.')
        for i in xrange(len(comps[:-1])):
            comps[i] = comps[i][:1]
        return prefix + '.'.join(comps)

    def display_tree(self, list):
        """construit un arbre directement à partir de la liste (nom, data)"""
        def format_node(item, depth):
            "Formate tout bien"
            # Selon qu'on est dans la liste des groupes, ou pas
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

            return [item[1]['name'], caption, item[1]['subd'], True, font]

        def grow_tree(root, list, depth):
            if len(list) == 1:
                self.group2node[list[0][1]['name']] = self.data.append(
                    root, format_node(list[0], depth))
                return
            branches = []
            subtrees = {}
            # Si jamais la hiérarchie correspond à un nœud
            node = None
            newroot = None
            for l in list:
                if len(l[0]) == depth:
                    # On a trouvé le nœud racine
                    node = l
                    continue
                if l[0][depth] not in subtrees:
                    subtrees[l[0][depth]] = [l]
                    branches.append(l[0][depth])
                else:
                    subtrees[l[0][depth]].append(l)
            if node:
                # Il y a un vrai groupe, on le met
                newroot = self.data.append(
                    root, format_node(node, depth))
                self.group2node[node[1]['name']] = newroot
            if (len(branches) > 1) and (depth > 0) and not(newroot):
                newroot = self.data.append(root, ["", ".".join(list[0][0][:depth]),
                                                  False, False, "normal"])
            if not(newroot): newroot = root
            for b in branches:
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
            if len(arts):
                digits = len(str(max([v for i, v in arts.iteritems()])))
            else:
                digits = 0
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
        nos = self.parent.conf.groups[self.popped_group]
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
                if len(nos) == 0:
                    nos.append([tagged_range[0], tagged_range[1]])
                else:
                    # Insertion du bouzin
                    for i in xrange(len(nos)):
                        if (tagged_range[0] - 1 <= nos[i][-1]):
                            if tagged_range[1] < nos[i][0] - 1:
                                nos[i:i] = [[tagged_range[0], tagged_range[1]]]
                                break
                            elif nos[i][0] - 1 <= tagged_range[1] :
                                nos[i] = [min(nos[i][0], tagged_range[0]),
                                          max(nos[i][-1], tagged_range[1])]
                            break
                    # Nettoyage
                    i = 1
                    while i < len(nos):
                        if (nos[i][0] - nos[i - 1][-1]) <= 1:
                            nos[i-1:i+1] = [[nos[i - 1][0],
                                             max(nos[i - 1][-1], nos[i][-1])]]
                            continue
                        i += 1
            dialog.destroy()
            self.refresh_tree()

    def popup_unkillarts(self, action):
        nos = self.parent.conf.groups[self.popped_group]
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
                i = 0
                while i < len(nos):
                    if tagged_range[0] <= nos[i][0]:
                        if tagged_range[1] >= nos[i][-1]:
                            # On enlève tout
                            del nos[i]
                            continue
                        else:
                            # On enlève par la gauche
                            nos[i][0] = tagged_range[1] + 1
                            break
                    if nos[i][0] < tagged_range[0]:
                        if nos[i][-1] > tagged_range[1]:
                            # On enlève au milieu
                            nos[i:i+1] = [[nos[i][0], tagged_range[0] - 1],
                                          [tagged_range[1] + 1, nos[i][-1]]]
                            break
                        else:
                            if nos[i][-1] >= tagged_range[0]:
                                # On enlève à droite
                                nos[i][-1] = tagged_range[0] - 1
                            i += 1
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

class SummaryBuffer:
    # Affichage du panneau Sommaire
    def display_tree(self, group, nb_start, nb_end, time_format = "%d %b %Y %H:%M"):
        """Crée un arbre de threads à partir d'une overview
           Renvoie un dictionnaire indexé par Msg-Id"""
        # On ne lit pas forum à des heures indues
        if not(flrn_config.is_geek_time(
                self.parent.conf.params['geek_start_time'],
            self.parent.conf.params['geek_end_time'])):
            print "C'est pas l'heure de lire forum !"
            self.parent.action_quit_callback()
            return False

        overview, vanished = self.parent.conf.server.overview(
            group, nb_start, nb_end)
        ids = set([i[4] for i in overview])
        xover = []
        lowest = nb_start

        # On cherche les parents
        for i in xrange(len(overview)):
            for t in xrange(len(overview[ - 1 - i][5])):
                ref_id = overview[ - 1 - i][5][- 1 - t]
                # Déja traité ?
                if ref_id in ids: continue
                art = self.parent.conf.server.get_article_by_msgid(ref_id)
                if not(art): continue
                # Sorti du conti ?
                if group not in art.headers['Newsgroups'].strip().split(','):
                    break
                # On trouve le numéro
                for xref in art.headers['Xref'].strip().split():
                    if xref.split(':')[0] == group:
                        art_no = int(xref.split(':')[1])
                        if art_no < lowest: lowest = art_no
                        break
                ids.add(ref_id)
                xover[0:0] = self.parent.conf.server.overview(
                    group, art_no, art_no)[0]
        
        if self.parent.conf.params['with_cousins']:
            # On ajoute les cousins
            overview2, vanished2 = self.parent.conf.server.overview(
                group, max(lowest, nb_start -
                           int(self.parent.conf.params['max_backtrack'])), 
                           nb_start - 1)
            vanished.extend(vanished2)
            # On vérifie quand même qu'ils font partie des bons threads
            for i in overview2:
                for t in xrange(len(i[5])):
                    ref_id = i[5][- 1 - t]
                    if ref_id in ids:
                        ids.add(i[4])
                        xover[0:0] = [i]
                        break
        xover.extend(overview)
        # On ajoute les enfants
        overview3, vanished3 = self.parent.conf.server.overview(
            group, nb_end + 1, nb_end 
            + int(self.parent.conf.params['max_backtrack']))
        vanished.extend(vanished3)
        for i in overview3:
            for t in xrange(len(i[5])):
                ref_id = i[5][- 1 - t]
                if ref_id in ids:
                    ids.add(i[4])
                    xover.append(i)
                    break
        # On trie
        i = 0
        while i < len(xover):
            j = i + 1
            while j < len(xover):
                while xover[j][0] == xover[i][0]: 
                    del xover[j]
                    if j == len(xover): break
                if j == len(xover): break
                if xover[j][4] in xover[i][5]:
                    xover[i], xover[j] = xover[j], xover[i]
                j += 1
            i += 1

        model = self.data
        model.clear()
        self.current_node = None
        try:
            del self.nodes
        except: pass
        self.nodes = {}
        read_list = self.parent.conf.groups[self.parent.current_group]
        # Les articles inexistants sont marqués comme lus dans le newsrc
        for i in vanished:
            self.parent.conf.register_read(self.parent.current_group, int(i))
        # Sélection des règles
        To_Apply = []
        for K in self.parent.conf.killrules:
            if K.group_match(group): To_Apply.append(K)
        
        for i in xover:
            number = int(i[0])
            read = False
            # Lu ?
            for j in read_list:
                read = read or (j[0] <= number <= j[-1])
            subject = nntp_io.translate_header(i[1])
            # Application des règles
            for K in To_Apply:
                if read == K.read_before:
                    heads = {
                        'Newsgroups': group,
                        'Subject': i[1],
                        'From': i[2],
                        'Date': i[3],
                        'Message-ID': i[4],
                        'References': ' '.join(i[5]) }
                    if K.article_match(heads):
                        read = K.read_after
                        if K.read_after:
                            flrn_config.debug_output(
                                u'[SumBuffer] Marqué ' 
                                + str(number) + ' comme lu ')
                            self.parent.conf.register_read(
                                self.parent.current_group, number)
                        else:
                            flrn_config.debug_output(
                                u'[SumBuffer] Marqué ' 
                                + str(number) + ' comme non lu ')
                            self.parent.conf.register_unread(
                                self.parent.current_group, number)
            # Auteur ?
            real_name, addr = email.Utils.parseaddr(
                nntp_io.translate_header(i[2]))
            if len(real_name) == 0: author = addr
            else: author = real_name
            date = time.strftime(time_format, email.Utils.parsedate(i[3]))
            msgid = i[4]
            if len(i[5]) > 0 and self.nodes.has_key(i[5][-1]):
                if model.get_value(self.nodes[i[5][-1]], 2) == subject:
                    # C'est le même sujet, on l'indique
                    self.nodes[msgid] = model.append(
                        self.nodes[i[5][-1]],
                        [msgid, number, subject, author, date, read, '...'])
                else:
                    self.nodes[msgid] = model.append(
                        self.nodes[i[5][-1]],
                        [msgid, number, subject, author, date, read, subject])
                    
            else:
                self.nodes[msgid] = model.append(
                    None,
                    [msgid, number, subject, author, date, read, subject])
        self.widget.set_model(model)
        self.widget.expand_all()
        
        # Informations
        self.parent.status_bar.pop(0)
        self.parent.status_bar.push(0, "Groupe " + self.parent.current_group)

    def get_next_row(self, iter):
        res = None
        # On essaie de prendre le fils
        ptr = self.data.iter_nth_child(iter, 0)
        if ptr: 
            return ptr
        else: 
            if not(iter): return None
            else: ptr = iter
            # Sinon, on prend le frère
            while not(self.data.iter_next(ptr)):
                # Ou l'oncle
                if not(self.data.iter_parent(ptr)):
                    return None
                else:
                    ptr = self.data.iter_parent(ptr)
            return self.data.iter_next(ptr)

    def select_article_callback(self, widget, data=None):
        """Affiche un article dans le buffer Article du parent"""
        model, art_iter = widget.get_selected()
        if not(art_iter): return False
        msgid = model.get_value(art_iter, 0)
        # Était-il lu ?
        if not(model.get_value(art_iter, 5)):
            model.set_value(art_iter, 5, True)
            # Mise à jour de la liste de lus
            self.parent.conf.register_read(self.parent.current_group,
                                           model.get_value(art_iter, 1))
            caption = self.parent.group_tab.data.get_value(
                self.parent.group_tab.group2node[self.parent.current_group],
                GRP_COLUMN_CAPTION).split(":")
            self.parent.group_tab.data.set_value(
                self.parent.group_tab.group2node[self.parent.current_group],
                GRP_COLUMN_CAPTION, str(int(caption[0]) - 1) + ':' + caption[1])
        self.current_node = art_iter
        self.parent.article_tab.display_msgid(msgid)
        # On recentre le cadre
        self.widget.scroll_to_cell(self.data.get_path(art_iter))
        
        # On affiche l'arbre 
        if self.parent.conf.params['small_tree']:
            path = model.get_path(art_iter)
            self.parent.tree_tab.make_tree(model, model.get_iter((path[0],)))
            self.parent.tree_tab.draw_tree()

    def activate_article_callback(self, widget, path, col, data=None):
        self.widget.get_selection().unselect_all()
        self.widget.get_selection().select_path(path)
        return False

    def changed_tree_callback(self, model, path, iter):
        '''Callback de mise à jour de l'arbre'''
        if self.current_node:
            self.parent.tree_tab.make_tree(
                model, model.get_iter((model.get_path(self.current_node)[0],)))
            self.parent.tree_tab.draw_tree()
        return False

    def read_toggle(self, iter, read):
        '''Change l'état et met à jour la liste de lus'''
        self.data.set_value(iter, SUM_COLUMN_READ, read)
        if read:
            # Marquer comme lu
            flrn_config.debug_output("[SumBuffer] Article %d lu" % 
                                     self.data.get_value(iter, SUM_COLUMN_NUM))
            self.parent.conf.register_read(
                self.parent.current_group,
                self.data.get_value(iter, SUM_COLUMN_NUM))
        else:
            # Marquer comme non lu
            flrn_config.debug_output("[SumBuffer] Article %d non lu" % 
                                     self.data.get_value(iter, SUM_COLUMN_NUM))
            self.parent.conf.register_unread(
                self.parent.current_group,
                self.data.get_value(iter, SUM_COLUMN_NUM))

    def read_toggle_callback(self, widget, path, data=None):
        '''Callback pour changer l'état'''
        self.read_toggle(
            self.data.get_iter(path),
            not self.data.get_value(self.data.get_iter(path), SUM_COLUMN_READ))

    def set_replies_read(self, iter, read):
        '''Modification d'état récursive'''
        self.read_toggle(iter, read)
        for i in xrange(self.data.iter_n_children(iter)):
            self.set_replies_read(self.data.iter_nth_child(iter, i), read)

    def click_callback(self, widget, event):
        if (event.type == gtk.gdk.BUTTON_PRESS) and event.button == 3:
            position = widget.get_path_at_pos(int(event.x), int(event.y))
            if not(position):
                return False
            row = self.data[position[0]]
            self.popped_article = row.iter
            self.popup_menushow(True, event)
            return True
        return False

    def popup_menushow(self, clicked, event=None):
        if not(clicked):
            path = self.widget.get_cursor()[0]
            if path:
                self.popped_article = self.data.get_iter(path)
            else: 
                return False
        # On affiche le menu
        popup_menu = self.ui_manager.get_widget("/ui/ContextMenu")
        popup_menu.show_all()
        if clicked: 
            popup_menu.popup(None, None, None, event.button, event.time)
        else:
            popup_menu.popup(None, None, None, None, None)

    # Actions du menu contextuel
    def popup_reply(self, action):
        self.widget.get_selection().select_iter(self.popped_article)
        self.parent.action_reply_callback(None)
        return True

    def popup_killreplies(self, action):
        self.set_replies_read(self.popped_article, True)
        return True

    def popup_unkillreplies(self, action):
        self.set_replies_read(self.popped_article, False)
        return True

    def __init__(self, pack_function, parent = None):
        self.parent = parent
        # Panneau de sommaire
        self.data = gtk.TreeStore(
            gobject.TYPE_STRING,  # 0:Msgid
            gobject.TYPE_INT,     # 1:Numéro
            gobject.TYPE_STRING,  # 2:Sujet
            gobject.TYPE_STRING,  # 3:From
            gobject.TYPE_STRING,  # 4:Date
            gobject.TYPE_BOOLEAN, # 5:Lu
            gobject.TYPE_STRING)  # 6:Truc à afficher

        self.container = gtk.ScrolledWindow()
        self.container.set_policy(gtk.POLICY_AUTOMATIC,
                                  gtk.POLICY_AUTOMATIC)
        self.container.set_property("height-request", 160)
        self.container.set_property("width-request", 500)
        pack_function(self.container)
        self.container.show()

        self.widget = gtk.TreeView(self.data)
        self.container.add(self.widget)
        self.widget.show()

        self.column_no = gtk.TreeViewColumn(
            u'Numéro', gtk.CellRendererText(), text=1)
        self.column_subj = gtk.TreeViewColumn(
            'Sujet', gtk.CellRendererText(), text=6)
        self.column_from = gtk.TreeViewColumn(
            'Auteur', gtk.CellRendererText(), text=3)
        self.column_date = gtk.TreeViewColumn(
            'Date', gtk.CellRendererText(), text=4)
        toggling_renderer = gtk.CellRendererToggle()
        self.column_read = gtk.TreeViewColumn(
            'Lu', toggling_renderer, active=5)
        self.column_subj.set_resizable(True)
        #self.column_subj.set_max_width(500)
        self.column_from.set_resizable(True)
        self.column_date.set_resizable(True)
        self.column_read.set_resizable(True)
        self.column_no.set_resizable(True)
        self.widget.append_column(self.column_read)
        self.widget.append_column(self.column_no)
        self.widget.append_column(self.column_from)
        self.widget.append_column(self.column_subj)
        self.widget.append_column(self.column_date)
        self.widget.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.widget.set_property("expander-column", self.column_subj)

        self.widget.get_selection().connect(
            "changed", self.select_article_callback)
        toggling_renderer.connect("toggled", self.read_toggle_callback)
        self.widget.connect("row-activated", self.activate_article_callback)

        # Et maintenant, un menu contextuel
        menu_xmldef = """
        <ui>
        <popup name="ContextMenu" action="PopupMenuAction">
        <menuitem name="Reply" action="ReplyAction"/>
        <menuitem name="KillReplies" action="KillRepliesAction"/>
        <menuitem name="UnkillReplies" action="UnkillRepliesAction"/>
        </popup>
        </ui>"""
        self.ui_manager = gtk.UIManager()
        self.ui_manager.add_ui_from_string(menu_xmldef)
        self.action_group = gtk.ActionGroup("PopupMenuActions")
        self.action_group.add_actions([
                ("PopupMenuAction", None, "", None, None, None),
                ("ReplyAction", None, u"_Répondre", None, 
                 u"Répondre à ce message", self.popup_reply),
                ("KillRepliesAction", None, u"_Marquer la suite comme lue", 
                 None, u"Marque comme lus les descendants de ce message",
                 self.popup_killreplies),
                ("UnkillRepliesAction", None, u"Marquer la suite comme _non lue", 
                 None, u"Marque comme non lus les descendants de ce message",
                 self.popup_unkillreplies)])
        self.ui_manager.insert_action_group(self.action_group, 0)
        self.widget.connect("button-press-event", self.click_callback)
        self.widget.connect("popup-menu", self.popup_menushow, False)
        
        # Variables
        self.popped_article = None
        self.current_node = None
        self.nodes = {}

class ArticleBuffer:
    def desusurpation(self, article):
        """En cas d'usurpation"""
        try:
            real_login = article.headers['Sender'].strip().split('@')[0]
            from_login = email.Utils.parseaddr(
                article.headers['From'].strip())[1].split('@')[0]
            if from_login != real_login:
                return article.headers['From'] + ' [' + real_login + ']'
            else:
                return article.headers['From']
        except KeyError:
            return article.headers['From']

    def insert_msgid_link(self, textbuf, string, iter):
        link_tag = textbuf.create_tag(None)
        link_tag.set_data("msgid-link", string)
        textbuf.insert_with_tags(iter, string, link_tag,
                                 textbuf.get_tag_table().lookup("link"))
        link_tag.connect("event", self.left_click_event)

    def insert_header(self, textbuf, header, article, iter):
        if header == u'Réponse à':
            if article.headers.has_key("References"):
                father = self.parent.conf.server.get_article_by_msgid(
                    article.headers['References'].split()[-1])
                if father:
                    textbuf.insert_with_tags_by_name(iter, u'Réponse à: ', "head_name")
                    textbuf.insert_with_tags_by_name(iter, self.desusurpation(father) + '\n', "head_content")
            return
        if header not in article.headers:
            return
        if header == 'From':
            # Pour le From, on précise le Sender si nécessaire
            textbuf.insert_with_tags_by_name(iter, 'From: ', "head_name")
            textbuf.insert_with_tags_by_name(iter, self.desusurpation(article) + '\n', "head_content")
        elif header == 'References':
            # Pour les références, on met des liens cliquables vers les Msg-IDs
            textbuf.insert_with_tags_by_name(iter, 'References: ', "head_name")
            for msgid in article.headers['References'].split():
                self.insert_msgid_link(textbuf, msgid, iter)
                textbuf.insert(iter, ' ')
            textbuf.insert(iter, '\n')
        else:
            textbuf.insert_with_tags_by_name(iter, header + ': ', "head_name")
            textbuf.insert_with_tags_by_name(iter, article.headers[header] + '\n', "head_content")
    
    def insert_body(self, textbuf, string, iter):
        pos = iter.get_offset()
        textbuf.insert_with_tags_by_name(iter, string, "body")

        # Recherche de msg-ids
        matches = msgid_regexp.finditer(string)
        if matches:
            for m in matches:
                # On applique un tag lien au msg-id trouvé
                link_tag = textbuf.create_tag(None)
                link_tag.set_data("msgid-link", m.group(1))
                textbuf.apply_tag(link_tag,
                                  textbuf.get_iter_at_offset(pos + m.start()),
                                  textbuf.get_iter_at_offset(pos + m.end()))
                textbuf.apply_tag_by_name("link",
                                          textbuf.get_iter_at_offset(pos + m.start()),
                                          textbuf.get_iter_at_offset(pos + m.end()))
                link_tag.connect("event", self.left_click_event)
        # Recherche de liens http
        matches = weblink_regexp.finditer(string)
        if matches:
            for m in matches:
                # On applique un tag lien au msg-id trouvé
                link_tag = textbuf.create_tag(None)
                link_tag.set_data("web-link", m.group(1))
                textbuf.apply_tag(link_tag,
                                  textbuf.get_iter_at_offset(pos + m.start()),
                                  textbuf.get_iter_at_offset(pos + m.end()))
                textbuf.apply_tag_by_name("link",
                                          textbuf.get_iter_at_offset(pos + m.start()),
                                          textbuf.get_iter_at_offset(pos + m.end()))
                link_tag.connect("event", self.left_click_event)

        # Coloriage
        regexps_to_color = [(quote1_regexp, "quote1"),
                            (quote2_regexp, "quote2"),
                            (quote3_regexp, "quote3")]
        for grep, tagname in regexps_to_color:
            matches = grep.finditer(string)
            if matches:
                for m in matches:
                    textbuf.apply_tag_by_name(
                        tagname,
                        textbuf.get_iter_at_offset(pos + m.start(1)),
                        textbuf.get_iter_at_offset(pos + m.end(1)))

        # Signature
        match = signature_regexp.search(string)
        if match:
            textbuf.apply_tag_by_name(
                "signature",
                textbuf.get_iter_at_offset(pos + match.start(1)),
                textbuf.get_end_iter())
    
    def display(self, article):
        """ article = class nntp_io.Article"""
        self.article = article
        self.buffer.set_text("")
        
        # En-têtes
        if self.writable:
            # Mode édition, on affiche tous les headers
            pos = self.buffer.get_start_iter()
            for h in article.headers:
                self.insert_header(self.buffer, h, article, pos)
        else:
            # Mode lecture, on affiche juste ce qu'il faut
            others = filter(
                lambda x: not(x in set(flrn_config.headers_nb)),
                article.headers.keys())

            # Headers normaux
            self.buffer_head.set_text("")
            pos = self.buffer_head.get_start_iter()
            for h in self.parent.conf.headers_list:
                if h not in self.parent.conf.headers_weak:
                    if h == "others":
                        for k in others:
                            if k not in self.parent.conf.headers_hide:
                                self.insert_header(self.buffer_head, 
                                                   k, article, pos)
                        continue
                    self.insert_header(self.buffer_head, h, article, pos)
                        
            # Les headers faibles doivent rejoindre le corps.
            pos = self.buffer.get_start_iter()
            for h in self.parent.conf.headers_weak:
                if h == "others":
                    for k in others:
                        if k not in self.parent.conf.headers_hide:
                            self.insert_header(self.buffer, k, article, pos)
                    continue
                self.insert_header(self.buffer, h, article, pos)

            # Un peu de place pour les en-têtes, hein.
            self.container.set_position(
                self.container.get_data("last_position"))
        # Le corps du message, enfin
        # Noter le \n pour matcher les débuts de lignes...
        if self.rot13:
            body = '\n' + article.body.encode(
                'rot_13', 'xmlcharrefreplace').decode('latin-1')
        else:
            body = '\n' + article.body
        self.insert_body(self.buffer, body, pos)
        
        # Si le buffer Article est rétréci, le regonfler :
        if not(self.writable) and (
            self.parent.panel_right.get_property("position") 
            == self.parent.panel_right.get_property("max_position")):
            self.parent.panel_right.set_position(
                self.parent.panel_right.get_data("last_position"))

    def display_msgid(self, art_msgid):
        art = self.parent.conf.server.get_article_by_msgid(art_msgid)
        if art:
            sum = self.parent.summary_tab
            if art_msgid in sum.nodes:
                # 1er cas : l'article est sélectionné dans le buffer Sommaire
                if (sum.data.get_path(sum.current_node) 
                    == sum.data.get_path(sum.nodes[art_msgid])):
                    self.display(art)
                    self.parent.current_article = art_msgid
                    self.parent.history.append(art_msgid)
                else:
                # 2e cas : l'article n'est pas sélectionné
                    sum.widget.get_selection().select_iter(sum.nodes[art_msgid])
            else:
                # 3e cas : il faut changer d'overview
                self.display(art)
                self.parent.current_article = art_msgid
                self.parent.history.append(art_msgid)                    
            return True
        else:
            self.parent.error_msgbox(u'Impossible de trouver le message ' + art_msgid)
            return False
        
    def left_click_event(self, tag, widget, event, pos):
        """En cas de clic sur un lien"""
        if (event.type != gtk.gdk.BUTTON_RELEASE) or (event.button != 1):
            return False
        if self.writable:
            return False
        if widget.get_buffer().get_selection_bounds():
            # C'est une sélection, on ne fait rien
            start, end = widget.get_buffer().get_selection_bounds()
            if start != end:
                # Au cas où on sélectionne un intervalle
                # de longueur nulle, on sait jamais
                return False

        # Lien vers un msg-id
        target = tag.get_data("msgid-link")
        if target:
            self.display_msgid(target)
        # Lien vers un site web
        target = tag.get_data("web-link")
        if target:
            os.spawnlp(os.P_NOWAIT, self.parent.conf.wwwbrowser,
                       self.parent.conf.wwwbrowser, target)
        return False

    def event_resize_head(self, widget, spec):
        pos = widget.get_property(spec.name)
        if pos != widget.get_property("max-position"):
            widget.set_data("last_position", pos)
        return False

    def set_rot13(self):
        self.rot13 = True; self.display(self.article)
    def unset_rot13(self):
        self.rot13 = False; self.display(self.article) 

    def __init__(self, article, editable, pack_function, parent = None):
        self.parent = parent
        # Contenant
        if editable:
            # Mode Édition: un seul panneau
            self.container = gtk.ScrolledWindow()
            self.container.set_policy(gtk.POLICY_AUTOMATIC,
                                      gtk.POLICY_AUTOMATIC)
        else:
            # Mode Lecture: deux panneaux (un pour les headers forts)
            self.container = gtk.VPaned()
            self.container.connect("notify::position",
                                   self.event_resize_head)
        pack_function(self.container)
        self.container.show()
        
        self.buffer = gtk.TextBuffer(self.parent.conf.tagtable)
        self.widget = gtk.TextView(self.buffer)
        self.writable = editable
        self.widget.set_property("editable", editable)
        # Important pour avoir des polices à largeur fixe
        self.widget.modify_font(pango.FontDescription("monospace"))
        self.widget.set_wrap_mode(gtk.WRAP_WORD)
        if editable:
            self.container.add(self.widget)
            self.widget.show()
        else:
            # Zone d'affichage du corps
            self.scrolled = gtk.ScrolledWindow()
            self.scrolled.set_policy(gtk.POLICY_AUTOMATIC,
                                     gtk.POLICY_AUTOMATIC)
            self.container.pack2(self.scrolled)
            self.scrolled.show()
            
            self.scrolled.add(self.widget)
            self.widget.show()
            # Zone d'zffichage des en-t€tes
            self.scrolled_head = gtk.ScrolledWindow()
            self.scrolled_head.set_policy(gtk.POLICY_AUTOMATIC,
                                          gtk.POLICY_AUTOMATIC)
            self.container.pack1(self.scrolled_head)
            self.scrolled_head.show()

            self.buffer_head = gtk.TextBuffer(self.parent.conf.tagtable)
            self.widget_head = gtk.TextView(self.buffer_head)
            self.widget_head.set_property("editable", False)
            self.widget_head.modify_font(pango.FontDescription("monospace"))
            self.widget_head.set_wrap_mode(gtk.WRAP_WORD)
            self.scrolled_head.add(self.widget_head)
            self.widget_head.show()

        self.article = article
        self.rot13 = False
        if article:
            self.display(article)

class ArticleEditor:
    def action_send_callback(self, action):
        # Formatage de l'article
        article = nntp_io.Article()
        article.from_utf8_text(self.article_widget.buffer.get_text(
            self.article_widget.buffer.get_start_iter(),
            self.article_widget.buffer.get_end_iter()).decode('utf-8'),
                               self.conf)

        # Enregistrement
        f, tmpfile = mkstemp("", ".flrn.article.", os.path.expanduser("~"))
        os.write(f, article.to_raw_format(self.conf))
        os.close(f)
        f = open(tmpfile, 'r')
        if article:
            # Demande de confirmation
            confirm = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                u'Êtes-vous sûr de vouloir envoyer le message ?')
            if (confirm.run() == gtk.RESPONSE_YES):
                # Envoi
                error = self.conf.server.post_article(f)
                confirm.destroy()
            else:
                confirm.destroy()
                return None
        else:
            error = u"Erreur lors de la préparation de l'article"
        if not(error):
            #self.parent.status_bar.push(0, u'Message envoyé')
            f.close()
            os.remove(tmpfile)
        else:
            dialog = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL,
                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                error + '\nMessage enregistré dans ' + tmpfile)
            f.close()
            dialog.run()
            dialog.destroy()
        self.window.event(gtk.gdk.Event(gtk.gdk.DELETE))
        del article
        
    def action_cancel_callback(self, action):
        self.window.event(gtk.gdk.Event(gtk.gdk.DELETE))

    def formatter_callback(self, widget, event):
        if event.string and (event.string in ' '):
            buffer = widget.get_buffer().get_text(
                widget.get_buffer().get_start_iter(),
                widget.get_buffer().get_end_iter()).decode('utf-8')
            iter = widget.get_buffer().get_iter_at_mark(
                widget.get_buffer().get_insert())
            # Si on édite les headers, on ne veut pas se retrouver 
            # à Trifouillis-les-Oies
            nb_heads = len(buffer.split('\n\n')[0].split('\n'))
            if nb_heads > iter.get_line():
                return False
            # Calcul des positions pour remettre le curseur au bon endroit
            anti_curpos = len(buffer) - iter.get_offset()
            anti_linepos = widget.get_buffer().get_line_count() - iter.get_line()
            curpos = iter.get_line_offset()
            
            article = nntp_io.Article()
            article.from_utf8_text(widget.get_buffer().get_text(
                    widget.get_buffer().get_start_iter(),
                    widget.get_buffer().get_end_iter()).decode('utf-8'),
                                   self.conf)
            lines = article.body.split('\n')
            if anti_linepos <= len(lines):
                if ((len(lines[len(lines) - anti_linepos]) > 72) 
                    and (curpos >= len(lines[len(lines) - anti_linepos]) - 2)):
                    lines[len(lines) - anti_linepos] = textwrap.fill(
                        lines[len(lines) - anti_linepos], width=76)
            article.body = '\n'.join(lines)
            self.article_widget.display(article)
            widget.get_buffer().place_cursor(widget.get_buffer().get_iter_at_offset(
                widget.get_buffer().get_char_count() - anti_curpos))
            return False
        return False
        
    def __init__(self, article, config):
        self.conf = config
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Éditeur d'article")
        self.window.set_default_size(900,600)

        self.vbox_main = gtk.VBox()
        self.window.add(self.vbox_main)

        # Barre d'outils
        toolbar_def = """
        <ui>
            <toolbar>
                <toolitem name="Send" action="SendAction"/>
                <toolitem name="Cancel" action="CancelAction"/>
            </toolbar>
        </ui>
        """
        self.ui_manager = gtk.UIManager()
        self.ui_manager.add_ui_from_string(toolbar_def)
        self.action_group = gtk.ActionGroup("EditorActions")
        self.action_group.add_actions([
            ("SendAction", gtk.STOCK_NETWORK, "Envoyer", "<control>P",
             "Envoyer l'article", self.action_send_callback),
            ("CancelAction", gtk.STOCK_CANCEL, "Annuler", "<control>Q",
             u"Annuler l'édition de l'article", self.action_cancel_callback)])
        self.ui_manager.insert_action_group(self.action_group, 0)
        self.window.add_accel_group(self.ui_manager.get_accel_group())

        # Zone d'édition
        self.vbox_main.pack_start(
            self.ui_manager.get_widget("/ui/toolbar"), False, False, 0)
        self.article_widget = ArticleBuffer(
            article, True, self.vbox_main.pack_start, self)
        self.article_widget.widget.connect("key-press-event", self.formatter_callback)
        
