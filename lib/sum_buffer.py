# -*- coding: utf-8 -*-

# Flrn-gtk: panneau sommaire
# Rémy Oudompheng, Noël 2005-Septembre 2006

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

import re

# Modules
import nntp_io
import flrn_config

from data_types import *

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
SUM_COLUMN_CAPTION = 6
SUM_COLUMN_COLOR = 7
SUM_COLUMN_FONT = 8

class SummaryBuffer:
    # Affichage du panneau Sommaire
    def display_tree(self, group, nb_start, nb_end,
                     time_format = "%d %b %Y %H:%M"):
        """Crée un arbre de threads à partir d'une overview
           Renvoie un dictionnaire indexé par Msg-Id"""
        # On ne lit pas forum à des heures indues
        if not(flrn_config.is_geek_time(
                self.parent.conf.params['geek_start_time'],
            self.parent.conf.params['geek_end_time'])):
            print "C'est pas l'heure de lire forum !"
            self.parent.action_quit_callback()
            return False

        data_source = self.parent.conf.overview_cache[group]
        # On prend d'avance ce qui nous intéresse
        data_source.get_overview(
            nb_start - self.parent.conf.params['max_backtrack'],
            nb_end   + self.parent.conf.params['max_foretrack'])
        overview, vanished = data_source.get_overview(nb_start, nb_end)
        ids = set([i[4] for i in overview])
        xover = []
        lowest = nb_start

        # On cherche les parents
        for i in xrange(-1, -1 - len(overview), -1):
            for t in xrange(-1, -1 - len(overview[i][5]), -1):
                ref_id = overview[i][5][t]
                # Déja traité ?
                if ref_id in ids: continue
                art = self.parent.conf.server.get_article_by_msgid(ref_id)
                if not(art): continue
                # Sorti du conti et numéro ?
                sorti = True
                for xref in art.headers['Xref'].strip().split():
                    if xref.split(':')[0] == group:
                        sorti = False
                        art_no = int(xref.split(':')[1])
                        if art_no < lowest: lowest = art_no
                        break
                if not(sorti):
                    ids.add(ref_id)
                    truc = data_source.get_item(art_no)
                    if truc: xover[0:0] = [truc]
        
        if self.parent.conf.params['with_cousins']:
            overview2, vanished2 = data_source.get_overview(
                max(lowest, nb_start -
                    int(self.parent.conf.params['max_backtrack'])), 
                nb_start - 1)
            vanished.extend(vanished2)

            # On vérifie quand même qu'ils font partie des bons threads
            for i in overview2:
                for t in xrange(-1, -1 - len(i[5]), -1):
                    ref_id = i[5][t]
                    if ref_id in ids:
                        ids.add(i[4])
                        xover[0:0] = [i]
                        break
        xover.extend(overview)
        # On ajoute les enfants
        overview3, vanished3 = data_source.get_overview(
            nb_end + 1, nb_end 
            + int(self.parent.conf.params['max_foretrack']))
        vanished.extend(vanished3)
        for i in overview3:
            for t in xrange(-1, -1-len(i[5]), -1):
                ref_id = i[5][t]
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
                if xover[j][4] in xover[i][5]:
                    xover[i], xover[j] = xover[j], xover[i]
                j += 1
            i += 1

        model = self.data
        model.clear()
        self.current_node = None
        if hasattr(self, 'nodes'): del self.nodes
        self.nodes = {}

        # Les articles inexistants sont marqués comme lus dans le newsrc
        for i in vanished:
            self.parent.conf.register_read(self.parent.current_group, int(i))
        # Sélection des règles
        To_Apply = []
        for K in self.parent.conf.killrules:
            if K.group_match(group): To_Apply.append(K)
        
        for i in xover:
            number = int(i[0])
            # Lu ?
            read = self.parent.conf.groups[self.parent.current_group].owns(number)
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
                            debug_output(
                                u'[SumBuffer] Marqué ' 
                                + str(number) + ' comme lu ')
                            self.parent.conf.register_read(
                                self.parent.current_group, number)
                        else:
                            debug_output(
                                u'[SumBuffer] Marqué ' 
                                + str(number) + ' comme non lu ')
                            self.parent.conf.register_unread(
                                self.parent.current_group, number)

            # Auteur ?
            real_name, addr = email.Utils.parseaddr(
                nntp_io.translate_header(i[2]))
            if len(real_name) == 0: author = addr
            else: author = real_name
            # Affichage du sujet
            caption = subject
            if (len(i[5]) > 0) and (i[5][-1] in self.nodes):
                if (model.get_value(self.nodes[i[5][-1]], 2) == subject):
                    # C'est le même sujet, on l'indique
                    caption = "..."
            # Autres données
            date = time.strftime(time_format, email.Utils.parsedate(i[3]))
            msgid = i[4]
            color = "black" 
            font = "bold" if not read else "normal"
            if not(nb_start <= number <= nb_end):
                color = "grey"
                font = "italic"
            choses_affichees = [msgid, number, subject, author,
                                date, read, caption, color, font]
            if len(i[5]) > 0 and self.nodes.has_key(i[5][-1]):
                self.nodes[msgid] = model.append(
                    self.nodes[i[5][-1]], choses_affichees)
            else:
                self.nodes[msgid] = model.append(
                    None, choses_affichees)
                
        self.widget.set_model(model)
        self.widget.expand_all()
        
        # Informations
        self.parent.group_tab.refresh_tree()
        
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
        if not(model.get_value(art_iter, SUM_COLUMN_READ)):
            self.read_toggle(art_iter, True)
        # Reprenons
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
        """Callback de mise à jour de l'arbre"""
        if self.current_node:
            self.parent.tree_tab.make_tree(
                model, model.get_iter((model.get_path(self.current_node)[0],)))
            self.parent.tree_tab.draw_tree()
        return False

    def read_toggle(self, iter, read, refresh=True):
        """Change l'état et met à jour la liste de lus"""
        self.data.set_value(iter, SUM_COLUMN_READ, read)
        self.data.set_value(iter, SUM_COLUMN_FONT,
                            "normal" if read else "bold")
        if read:
            # Marquer comme lu
            debug_output("[SumBuffer] Article %d lu" % 
                                     self.data.get_value(iter, SUM_COLUMN_NUM))
            self.parent.conf.register_read(
                self.parent.current_group,
                self.data.get_value(iter, SUM_COLUMN_NUM))
        else:
            # Marquer comme non lu
            debug_output("[SumBuffer] Article %d non lu" % 
                                     self.data.get_value(iter, SUM_COLUMN_NUM))
            self.parent.conf.register_unread(
                self.parent.current_group,
                self.data.get_value(iter, SUM_COLUMN_NUM))
        if refresh: self.parent.group_tab.refresh_tree()

    def read_toggle_callback(self, widget, path, data=None):
        """Callback pour changer l'état"""
        self.read_toggle(
            self.data.get_iter(path),
            not self.data.get_value(self.data.get_iter(path), SUM_COLUMN_READ))

    def set_replies_read(self, iter, read):
        """Modification d'état récursive"""
        self.read_toggle(iter, read, False)
        for i in xrange(self.data.iter_n_children(iter)):
            self.set_replies_read(
                self.data.iter_nth_child(iter, i), read)

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
            gobject.TYPE_STRING,  # 6:Truc à afficher
            gobject.TYPE_STRING,  # 7:Couleur
            gobject.TYPE_STRING)  # 8:Police

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
            u'Numéro', gtk.CellRendererText(),
            text=SUM_COLUMN_NUM, font=SUM_COLUMN_FONT,
            foreground=SUM_COLUMN_COLOR)
        self.column_subj = gtk.TreeViewColumn(
            'Sujet', gtk.CellRendererText(),
            text=SUM_COLUMN_SUBJ, font=SUM_COLUMN_FONT,
            foreground=SUM_COLUMN_COLOR)
        self.column_from = gtk.TreeViewColumn(
            'Auteur', gtk.CellRendererText(),
            text=SUM_COLUMN_FROM, font=SUM_COLUMN_FONT,
            foreground=SUM_COLUMN_COLOR)
        self.column_date = gtk.TreeViewColumn(
            'Date', gtk.CellRendererText(),
            text=SUM_COLUMN_DATE, font=SUM_COLUMN_FONT,
            foreground=SUM_COLUMN_COLOR)
        toggling_renderer = gtk.CellRendererToggle()
        self.column_read = gtk.TreeViewColumn(
            'Lu', toggling_renderer,
            active=SUM_COLUMN_READ)
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
