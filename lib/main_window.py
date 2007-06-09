#! /usr/bin/env python2.4
# -*- coding: utf-8 -*-

# Flrn-gtk: fenêtre principale
# Rémy Oudompheng, Noël 2005

import os
import sys
import time, re
import socket

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango
from tempfile import mkstemp

# Modules
from grp_buffer import *
import art_buffer
import nntp_io
import flrn_config

def remember_sep_height_callback(widget, spec):
    pos = widget.get_property(spec.name)
    if pos != widget.get_property("max-position"):
        widget.set_data("last_position", pos)
    return False

class SkelMainWindow:
    # Callbacks
    def select_group_callback(self, widget, data=None):
        model, group = widget.get_selected()
        if group:
            # On vérifie que c'est un vrai groupe.
            if model.get_value(group, GRP_COLUMN_ISREAL):
                self.current_group = model.get_value(
                    group, GRP_COLUMN_NAME)
                # Premier message non-lu
                try:
                    first, last = self.conf.server.group_stats(
                        self.current_group)
                except socket.error:
                    self.error_msgbox(u'Impossible de contacter le serveur')
                    self.action_quit_callback()
                    return
                read = self.conf.groups[self.current_group]
                if len(read) > 0 and read[0][0] == first:
                    first = read[0][-1] + 1
                    # S'il n'y a pas de nouveaux messages, autant afficher les derniers.
                    if first > last:
                        first = last - 20
                # Pour éviter de devoir télécharger une overview géante
                if last > first + 200:
                    self.action_overview_callback(None, [first, last])
                    return
                self.summary_tab.display_tree(self.current_group, first, last)
                self.panel_right.set_position(
                    self.panel_right.get_property("max_position"))

    def editor_die_callback(self, event, widget, data):
        data.window.destroy()
        del data

    # Menu Groupes
    def action_grpgoto_callback(self, action):
        # Boîte de sélection
        dialog = gtk.Dialog(u'Aller dans un groupe',
                            self.window, gtk.DIALOG_MODAL,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK,
                             gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
        dialog.vbox.pack_start(gtk.Label("Choisissez un groupe"),
                               False, False, 5)
        group_widget = GroupBuffer(self, dialog.vbox.pack_start)
        group_widget.display_tree(True)
        dialog.vbox.show_all()
        dialog.set_default_size(400, 500)
        dialog.user_data = None
        # Récupération de la sélection
        def get_user_entry(widget, resp_id):
            if resp_id == gtk.RESPONSE_OK:
                model, row = group_widget.widget.get_selection().get_selected()
                if row:
                    # On vérifie que c'est un vrai groupe.
                    if model.get_value(row, GRP_COLUMN_ISREAL):
                        widget.user_data = model.get_value(
                            row, GRP_COLUMN_NAME)

        dialog.connect("response", get_user_entry)
        if dialog.run() == gtk.RESPONSE_OK:
            if dialog.user_data:
                self.current_group = dialog.user_data
                # Premier message non-lu
                first, last = self.conf.server.group_stats(self.current_group)
                if ((len(self.conf.groups[self.current_group]) == 0)
                    or (self.conf.groups[self.current_group][0][0] > 1)):
                    first = 1
                else:
                    first = self.conf.groups[self.current_group][0][-1] + 1
                self.summary_tab.display_tree(self.current_group, first, last)
                self.panel_right.set_position(
                    self.panel_right.get_property("max_position"))
        dialog.destroy()

    def action_subscribe_callback(self, action):
        """Affiche une boîte de dialogue pour gérer les abonnements"""
        # Boîte de dialogue
        dialog = gtk.Dialog(u'Gérer les abonnements aux groupes',
                            self.window, gtk.DIALOG_MODAL,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK,
                             gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
        dialog.vbox.pack_start(gtk.Label(
            u"Cochez les groupes que vous souhaitez lire"), False, False, 5)
        # Un arbre avec des cases à cocher
        group_widget = GroupBuffer(self, dialog.vbox.pack_start, True)
        group_widget.display_tree(True)

        dialog.vbox.show_all()
        dialog.set_default_size(400, 550)

        # Récupération de la sélection
        subscriptions = []
        def mark_as_subscribed(model, path, iter, data):
            if model.get_value(iter, GRP_COLUMN_ISREAL):
                # C'est un vrai groupe
                data.append(
                    (model.get_value(iter, GRP_COLUMN_NAME),
                     model.get_value(iter, GRP_COLUMN_SUBSCRIBED)))
                
        def get_user_entry(widget, resp_id, data):
            if resp_id == gtk.RESPONSE_OK:
                treemodel = group_widget.widget.get_model()
                treemodel.foreach(mark_as_subscribed, subscriptions)

        dialog.connect("response", get_user_entry, subscriptions)
        if dialog.run() == gtk.RESPONSE_OK:
            # Enregistrement des abonnements
            for g, sub in subscriptions:
                if (g in self.conf.unsubscribed) and sub:
                    self.conf.subscribed.add(g)
                    self.conf.unsubscribed.remove(g)
                if (g in self.conf.subscribed) and not(sub):
                    self.conf.unsubscribed.add(g)
                    self.conf.subscribed.remove(g)
            # Mise à jour de l'affichage
            self.conf.update_groupsize()
            self.conf.update_unreads()
            self.group_tab.display_tree(False)
        dialog.destroy()

    def action_syncgroups_callback(self, action):
        self.conf.refresh_groups()
        self.conf.update_groupsize()
        self.group_tab.display_tree(False)

    # Menu Sommaire
    def action_sumgoto_callback(self, action):
        if self.current_group:
            vals = self.conf.server.group_stats(self.current_group)
            if vals:
                # Préparation de la boîte de dialogue
                dialog = gtk.Dialog(u"Voir l'article numéro...",
                                    self.window, gtk.DIALOG_MODAL,
                                    (gtk.STOCK_OK, gtk.RESPONSE_OK))
                step = int((vals[1] - vals[0]) / 5000) * 100 + 100
                num_entry = gtk.SpinButton(
                    gtk.Adjustment(1, vals[0], vals[1], 1, step))
                hbox = gtk.HBox()
                hbox.pack_start(gtk.Label(u"Numéro de l'article "),
                                False, False, 0)
                hbox.pack_start(num_entry, True, True, 0)
                dialog.vbox.pack_start(
                    gtk.Label(u"Groupe : " + self.current_group),
                    False, False, 0)
                dialog.vbox.pack_start(hbox, True, True, 0)
                dialog.vbox.show_all()

                # Récupération de la réponse
                dialog.artno = None
                def get_user_entry(widget, resp_id):
                    if resp_id == gtk.RESPONSE_OK:
                        widget.artno = num_entry.get_value_as_int()
                        return None
                dialog.connect("response", get_user_entry)
                
                if dialog.run() == gtk.RESPONSE_OK:
                    # Recherche du Message-ID
                    msgid = self.conf.server.get_by_artno(
                        self.current_group, dialog.artno)
                    if msgid:
                        self.article_tab.display_msgid(msgid)
                    else:
                        self.error_msgbox(u'Impossible de trouver le message '
                                          + self.current_group + ':' + str(dialog.artno))
                dialog.destroy()

    def action_overview_callback(self, action, default = None):
        """Affiche le sommaire entre deux numéros d'articles."""
        if self.current_group:
            vals = self.conf.server.group_stats(self.current_group)
            if vals:
                # Préparation de la boîte de dialogue
                dialog = gtk.Dialog(u"Voir le sommaire du groupe",
                                    self.window, gtk.DIALOG_MODAL,
                                    (gtk.STOCK_OK, gtk.RESPONSE_OK))
                if not(default): default = vals
                step = int((vals[1] - vals[0]) / 5000) * 100 + 100
                start_entry = gtk.SpinButton(
                    gtk.Adjustment(default[0], vals[0], vals[1], 1, step))
                end_entry = gtk.SpinButton(
                    gtk.Adjustment(default[1], vals[0], vals[1], 1, step))
                hbox = gtk.HBox()
                hbox.pack_start(gtk.Label(u"Voir les numéros "),
                                False, False, 0)
                hbox.pack_start(start_entry, True, True, 0)
                hbox.pack_start(gtk.Label(u" à "), False, False, 0)
                hbox.pack_start(end_entry, True, True, 0)
                
                dialog.vbox.pack_start(
                    gtk.Label(u"Groupe : " + self.current_group),
                    False, False, 0)
                dialog.vbox.pack_start(hbox, True, True, 0)
                dialog.vbox.show_all()
                
                # Récupération de la réponse
                dialog.summary_range = None
                def get_user_entry(widget, resp_id):
                    if resp_id == gtk.RESPONSE_OK:
                        widget.summary_range = [
                            start_entry.get_value_as_int(),
                            end_entry.get_value_as_int()]
                        return None
                dialog.connect("response", get_user_entry)
                
                if dialog.run() == gtk.RESPONSE_OK:
                    self.summary_tab.display_tree(
                        self.current_group,
                        min(dialog.summary_range),
                        max(dialog.summary_range))
                    self.panel_right.set_position(
                        self.panel_right.get_property("max_position"))
                dialog.destroy()
        else:
            dialog = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, 
                gtk.BUTTONS_CLOSE, u"Vous n'êtes dans aucun groupe. " +
                u"Entrez dans un groupe (en double-cliquant dessus, par " +
                u"exemple), et réessayez ensuite")

    def action_nextunread_callback(self, action):
        iter = self.summary_tab.current_node
        while not(iter) or self.summary_tab.data.get_value(iter, 5):
            # C'est lu, on passe à la suite
            iter = self.summary_tab.get_next_row(iter)
            if not(iter):
                for g in self.conf.unreads:
                    if self.conf.unreads[g] > 0:
                        # Ah ! Des messages non lus !
                        self.current_group = g
                        path = self.group_tab.data.get_path(
                            self.group_tab.group2node[self.current_group])
                        self.group_tab.widget.scroll_to_cell(path)
                        # On y va
                        self.group_tab.widget.get_selection().select_path(path)
                        self.select_group_callback(
                            self.group_tab.widget.get_selection())
                        return
                # Rien du tout, on met à jour le Group Buffer et les unreads
                self.conf.update_groupsize()
                self.group_tab.refresh_tree()
                return

        # On sélectionne le nœud en question
        self.summary_tab.widget.get_selection().unselect_all()
        self.summary_tab.widget.get_selection().select_iter(iter)
 
    # Fonctions de (de|con)struction massive
    def action_setreplies_callback(self, read):
        root = None
        if self.summary_tab.current_node:
            root = self.summary_tab.current_node
        elif self.summary_tab.widget.get_selection().get_selected()[1]:
            root = self.summary_tab.widget.get_selection().get_selected()[1]
        else:
            root = self.summary_tab.data.get_iter_first()
        if root: 
            self.summary_tab.set_replies_read(root, read)

    def action_setthread_callback(self, read):
        if read:
            dialog = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO, u'Attention : êtes-vous sûr(e) de vouloir'
                u" marquer comme lus TOUS les messages ayant un ancêtre commun"
                u" avec le message sélectionné ?")
        else:
            dialog = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO, u'Attention : êtes-vous sûr(e) de vouloir'
                u" marquer comme non lus TOUS les messages ayant un ancêtre"
                u" commun avec le message sélectionné ?")
        if dialog.run() == gtk.RESPONSE_YES:
            # On cherche un message-cible
            root = None
            if self.summary_tab.current_node:
                root = self.summary_tab.current_node
            elif self.summary_tab.widget.get_selection().get_selected()[1]:
                root = self.summary_tab.widget.get_selection().get_selected()[1]
            else:
                root = self.summary_tab.data.get_iter_first()
            # On récupère l'ID de son ancêtre
            ref = self.conf.server.get_article_by_msgid(
                self.summary_tab.data.get_value(root, 0))
            if 'References' in ref.headers:
                msgid = ref.headers['References'].split()[0]
            else:
                msgid = ref.headers['Message-ID']
            # On cherche les victimes parmi les éléments de profondeur 0
            for i in xrange(self.summary_tab.data.iter_n_children(None)):
                article = self.conf.server.get_article_by_msgid(
                    self.summary_tab.data.get_value(
                        self.summary_tab.data.iter_nth_child(None, i), 0))
                if article.headers['Message-ID'] == msgid:
                    self.summary_tab.set_replies_read(
                        self.summary_tab.data.iter_nth_child(None, i), read)
                    continue
                if 'References' in article.headers:
                    if msgid == article.headers['References'].split()[0]:
                        self.summary_tab.set_replies_read(
                            self.summary_tab.data.iter_nth_child(None, i), read)
        dialog.destroy()
    
    def action_killreplies_callback(self, action):
        self.action_setreplies_callback(True)
        return True
    def action_killthread_callback(self, action):
        self.action_setthread_callback(True)
        return True
    def action_unkillreplies_callback(self, action):
        self.action_setreplies_callback(False)
        return True
    def action_unkillthread_callback(self, action):
        self.action_setthread_callback(False)
        return True

    def action_savetreeasimage(self, action):
        dialog = gtk.FileSelection("Fichier de destination")
        dialog.set_filename("tree.png")
        if (dialog.run() == gtk.RESPONSE_OK):
            name = dialog.get_filename()
        else: return
        dialog.destroy()

        width, height = self.tree_tab.pictsize
        
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 
                                False, 8, width, height) 
        pixbuf.get_from_drawable(self.tree_tab.pixmap, 
                                 self.tree_tab.pixmap.get_colormap(), 
                                 0, 0, 0, 0, width, height)
        pixbuf.save(name, "png")

    # Menu Articles
    def action_new_callback(self, action):
        draft = nntp_io.Article()
        draft.headers['From'] = self.conf.from_header
        if self.current_group:
            draft.headers['Newsgroups'] = self.current_group
        else:
            draft.headers['Newsgroups'] = ""
        draft.headers['Subject'] = "(mettre un sujet)"
        editor = art_buffer.ArticleEditor(draft, self.conf)
        editor.window.connect("delete_event",
                              self.editor_die_callback, editor)
        editor.window.show_all()

    def action_reply_callback(self, action):
        if self.current_article:
            original = self.conf.server.get_article_by_msgid(
                self.current_article)
            draft = self.conf.make_reply(original)
            del original
            editor = art_buffer.ArticleEditor(draft, self.conf)
            editor.window.connect("delete_event",
                                  self.editor_die_callback, editor)
            editor.window.show_all()
            
    def action_cancel_callback(self, action):
        if self.current_article:
            # On récupère l'original
            original = self.conf.server.get_article_by_msgid(
                self.current_article)
            # Avertissement si on n'est pas sur la bonne machine
            if original.headers['Sender'].strip() != self.conf.params['mail_addr']:
                dialog = gtk.MessageDialog(
                    self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                    gtk.BUTTONS_CLOSE,
                    u"Attention ! Vous n'êtes peut-être pas autorisé à effacer ce message. Vérifiez que vous en êtes l'auteur et que vous vous trouvez sur la machine d'où ce message a été envoyé.")
                dialog.run()
                dialog.destroy()
            # Confirmation
            confirm = gtk.MessageDialog(
                self.window, gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                u'Êtes-vous sûr de vouloir annuler ce message ?')
            if (confirm.run() == gtk.RESPONSE_YES):
                confirm.destroy()
                
                # Préparation du message
                cancel_msg = nntp_io.Article()
                cancel_msg.headers['From'] = self.conf.from_header
                cancel_msg.headers['Newsgroups'] = self.current_group
                cancel_msg.headers['Subject'] = 'cancel'
                cancel_msg.headers['Control'] = 'cancel ' + self.current_article
                cancel_msg.body = self.conf.params['cancel_message'] + '\n'
                
                # Enregistrement
                f, tmpfile = mkstemp("", ".flrn.article.", os.path.expanduser("~"))
                os.write(f, cancel_msg.to_raw_format(self.conf))
                del cancel_msg
                os.close(f)
                f = open(tmpfile, 'r')
                # Envoi
                error = self.conf.server.post_article(f)
                if error:
                    dialog = gtk.MessageDialog(
                        self.window, gtk.DIALOG_MODAL,
                        gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                        u'Erreur. Réponse du serveur : ' + error)
                else:
                    dialog = gtk.MessageDialog(
                        self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                        gtk.BUTTONS_OK, u'Message envoyé.')
                dialog.run()
                dialog.destroy()
                f.close()
                os.remove(tmpfile)
            else:
                confirm.destroy()

    def action_supsede_callback(self, action):
        if self.current_article:
            # On récupère l'original
            draft = self.conf.server.get_article_by_msgid(self.current_article)
            # Avertissement si on n'est pas sur la bonne machine
            if (draft.headers['Sender'].strip()
                != self.conf.params['mail_addr']):
                dialog = gtk.MessageDialog(self.window,
                    gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                    u"Attention ! Vous n'êtes peut-être pas autorisé à modifier ce message. Vérifiez que vous en êtes l'auteur et que vous vous trouvez sur la machine d'où ce message a été envoyé.")
                dialog.run()
                dialog.destroy()

            # On met un Supersedes et on vire les headers spéciaux
            draft.headers['Supersedes'] = self.current_article
            for h in draft.headers.keys():
                if h in self.conf.supersede_remove_headers:
                    del draft.headers[h]

            editor = art_buffer.ArticleEditor(draft, self.conf)
            editor.window.connect("delete_event",
                                  self.editor_die_callback, editor)
            editor.window.show_all()

    def action_goto_parent_callback(self, action):
        if self.current_article:
            source = nntp_io.Article()
            source.from_nntplib(
                self.conf.server.get_by_msgid(self.current_article))
            if source.headers.has_key('References'):
                dest = source.headers['References'].split()[-1]
                if not(self.article_tab.display_msgid(dest)):
                    self.error_msgbox(u'Impossible de trouver le message père')
        return False

    def action_msgidgoto_callback(self, action):
        dialog = gtk.Dialog(u"Voir l'article correpondant à un Message-ID",
                            self.window, gtk.DIALOG_MODAL,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK))
        msgid_entry = gtk.Entry()
        dialog.vbox.pack_start(gtk.Label(u"Entrez un Message-ID"),
                               False, False, 0)
        dialog.vbox.pack_start(msgid_entry, False, False, 0)
        dialog.vbox.show_all()
        dialog.msgid = ""
        
        def get_user_entry(widget, resp_id):
            if resp_id == gtk.RESPONSE_OK:
                widget.msgid = msgid_entry.get_text()
            return None
        
        dialog.connect("response", get_user_entry)
        if dialog.run() == gtk.RESPONSE_OK:
            if not(self.article_tab.display_msgid(dialog.msgid)):
                self.error_msgbox(u'Impossible de trouver le message '
                                  + dialog.msgid)
        dialog.destroy()
    
    def action_msgviewraw_callback(self, action):
        if self.current_article:
            source = self.conf.server.get_by_msgid(self.current_article)

            # Préparation de la fenêtre
            dialog = gtk.Dialog(u"Affichage du message " + self.current_article,
                                self.window, gtk.DIALOG_MODAL,
                                (gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
            text_buffer = gtk.TextBuffer(self.conf.tagtable)
            text_widget = gtk.TextView(text_buffer)
            text_widget.set_property("editable", False)
            text_widget.modify_font(pango.FontDescription("monospace"))
            text_container = gtk.ScrolledWindow()
            text_container.set_policy(gtk.POLICY_AUTOMATIC,
                                      gtk.POLICY_AUTOMATIC)
            text_container.add_with_viewport(text_widget)

            dialog.vbox.pack_start(text_container, True, True, 0)
            dialog.vbox.show_all()
            dialog.set_default_size(600, 400)

            for l in source[0]:
                if ':' in l:
                    name, text = l.split(':', 1)
                    text_buffer.insert_with_tags_by_name(
                        text_buffer.get_end_iter(),
                        name.decode("latin-1") + ': ', "head_name")
                else:
                    text = l
                text_buffer.insert_with_tags_by_name(
                    text_buffer.get_end_iter(),
                    text.decode("latin-1") + '\n', "head_content")
            text_buffer.insert(text_buffer.get_end_iter(), '\n')
            for l in source[1]:
                text_buffer.insert_with_tags_by_name(
                    text_buffer.get_end_iter(),
                    l.decode("latin-1") + '\n', "body")
            dialog.run()
            dialog.destroy()

    def action_rot13ify_callback(self, action):
        if action.get_active():
            self.article_tab.set_rot13()
        else:
            self.article_tab.unset_rot13()

    def action_history_callback(self, action):
        # Préparation de la fenêtre
        dialog = gtk.Dialog(u'Historique', self.window, gtk.DIALOG_MODAL,
                            (gtk.STOCK_OK, gtk.RESPONSE_OK,
                             gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
        list_data = gtk.ListStore(gobject.TYPE_STRING,
                                  gobject.TYPE_STRING,
                                  gobject.TYPE_STRING,
                                  gobject.TYPE_STRING)
        list_data.clear()
        for msgid in self.history:
            heads = self.conf.server.cache[msgid].headers
            list_data.prepend(
                [heads['Subject'], heads['From'],
                 heads['Xref'].split()[1], msgid])
        list_widget = gtk.TreeView(list_data)
        list_widget.set_model(list_data)

        list_widget.append_column(gtk.TreeViewColumn(
            u'Sujet', gtk.CellRendererText(), text=0))
        list_widget.append_column(gtk.TreeViewColumn(
            u'Auteur', gtk.CellRendererText(), text=1))
        list_widget.append_column(gtk.TreeViewColumn(
            u'Groupe et numéro', gtk.CellRendererText(), text=2))
        list_widget.append_column(gtk.TreeViewColumn(
            u'Message-ID', gtk.CellRendererText(), text=3))
        list_container = gtk.ScrolledWindow()
        list_container.add(list_widget)
        list_container.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        dialog.vbox.pack_start(
            gtk.Label(u"Messages lus dans cette session\n" +
                      "(dans l'ordre chronologique inverse)"),
            False, False, 5)
        dialog.vbox.pack_start(list_container)
        dialog.vbox.show_all()
        dialog.set_default_size(400, 500)
        
        if dialog.run() == gtk.RESPONSE_OK:
            model, item = list_widget.get_selection().get_selected()
            msgid = list_data.get_value(item, 3)
            self.article_tab.display(self.conf.server.cache[msgid])
        dialog.destroy()
        
    def action_quit_callback(self, foo=None, bar=None):
        """Quitte le programme"""
        self.window.destroy()
        self.conf.save_newsrc()
        gtk.main_quit()
        return False

    def action_quit_kill_callback(self, foo=None, bar=None):
        """Quitte le programme sans sauver le newsrc"""
        self.window.destroy()
        try: self.tree_tab.window.visible = 0
        except KeyError: pass
        gtk.main_quit()
        return False

    def create_article_tagtable(self, config):
        item = gtk.TextTagTable()
        # En-Têtes
        tag = gtk.TextTag("head_name")
        tag.set_property("style", pango.STYLE_ITALIC)
        tag.set_property("foreground", "SeaGreen")
        item.add(tag)
        tag = gtk.TextTag("head_content")
        tag.set_property("style", pango.STYLE_ITALIC)
        tag.set_property("foreground", "DarkSlateGray")
        item.add(tag)
        # Corps de l'article
        tag = gtk.TextTag("body")
        item.add(tag)
        tag = gtk.TextTag("signature")
        tag.set_property("weight", pango.WEIGHT_BOLD)
        tag.set_property("foreground", "MidnightBlue")
        item.add(tag)
        # Liens
        tag = gtk.TextTag("link")
        tag.set_property("underline", pango.UNDERLINE_SINGLE)
        tag.set_property("foreground", "blue")
        item.add(tag)
        # Citations
        tag = gtk.TextTag("quote1")
        tag.set_property("style", pango.STYLE_OBLIQUE)
        tag.set_property("foreground", "DarkRed")
        item.add(tag)
        tag = gtk.TextTag("quote2")
        tag.set_property("style", pango.STYLE_OBLIQUE)
        tag.set_property("foreground", "ForestGreen")
        item.add(tag)
        tag = gtk.TextTag("quote3")
        tag.set_property("style", pango.STYLE_OBLIQUE)
        tag.set_property("foreground", "DarkCyan")
        item.add(tag)
        return item

    def error_msgbox(self, string):
        """À invoquer en cas de NNTPError"""
        dialog = gtk.MessageDialog(
            self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
            gtk.BUTTONS_CLOSE, string)
        dialog.run()
        dialog.destroy()
    
    def init_common(self, conf_source):
        # Configuration
        self.conf = conf_source
        self.conf.tagtable = self.create_article_tagtable(self.conf)
        # On vérifie s'il y a besoin d'une authentification
        if self.conf.server.needs_auth:
            auth_dlg = gtk.Dialog(
                "Authentification", None,
                gtk.DIALOG_MODAL, 
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                 gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
            # Un petit message.
            warning_label = gtk.Label()
            warning_label.set_markup(
                u'<span foreground="red"><big><b>Attention ! ' +
                u'Ce serveur nécessite une authentification par '+
                u"mot de passe. CE N'EST PAS le mot de passe " +
                u'qui vous sert à vous connecter sur les ordinateurs.' +
                u'</b></big></span>')
            warning_label.set_line_wrap(True)
            # La boîte d'entrée du login
            hbox1 = gtk.HBox()
            hbox1.pack_start(gtk.Label("Login"), False, False, 5)
            user_entry = gtk.Entry()
            hbox1.pack_start(user_entry, True, True, 0)
            # La boîte d'entré du password
            hbox2 = gtk.HBox()
            hbox2.pack_start(gtk.Label("Mot de passe"), False, False, 5)
            pass_entry = gtk.Entry()
            pass_entry.set_property("visibility", False)
            hbox2.pack_start(pass_entry, True, True, 0)
            
            auth_dlg.vbox.pack_start(warning_label)
            auth_dlg.vbox.pack_start(hbox1)
            auth_dlg.vbox.pack_start(hbox2)
            auth_dlg.vbox.show_all()

            ptr = []
            def get_data(widget, resp_id, data):
                if resp_id == gtk.RESPONSE_OK:
                    data.append(hbox1.get_text())
                    data.append(hbox2.get_text())
            auth_dlg.connect("response", get_data, ptr)
            if auth_dlg.run() == gtk.RESPONSE_OK:
                self.conf.server.authenticate(ptr[0], ptr[1])
                auth_dlg.destroy()
            else: 
                auth_dlg.destroy()
                sys.exit(0)


        # La définition des menus et boutons
        xml_source = """
        <ui>
            <menubar>
                <menu name="GrpMenu" action="GrpMenuAction">
                    <menuitem name="GrpGoto" action="GrpGotoAction"/>
                    <menuitem name="Subscribe" action="SubscribeAction"/>
                    <menuitem name="GrpSync" action="GrpSyncAction"/>
                </menu>
                <menu name="SumMenu" action="SumMenuAction">
                    <menuitem name="SumGoto" action="SumGotoAction"/>
                    <menuitem name="Overview" action="OverviewAction"/>
                    <separator/>
                    <menuitem name="NextUnread" action="NextUnreadAction"/>
                    <menuitem name="ZapReplies" action="ZapRepliesAction"/>
                    <menuitem name="ZapThread" action="ZapThreadAction"/>
                    <menuitem name="UnzapReplies" action="UnzapRepliesAction"/>
                    <menuitem name="UnzapThread" action="UnzapThreadAction"/>
                    <separator/>
                    <menuitem name="SaveTreeAsImage" action="SaveTreeAsImageAction"/>
                </menu>
                <menu name="ArtMenu" action="ArtMenuAction">
                    <menuitem name="New" action="NewAction"/>
                    <menuitem name="Reply" action="ReplyAction"/>
                    <menuitem name="Cancel" action="CancelAction"/>
                    <menuitem name="Supersede" action="SupsedeAction"/>
                    <separator/>
                    <menuitem name="ParentGoto" action="GotoParentAction"/>
                    <menuitem name="MsgidGoto" action="MsgidGotoAction"/>
                    <menuitem name="MsgViewRaw" action="MsgViewRawAction"/>
                    <menuitem name="MsgRot13ify" action="MsgRot13Action"/>
                </menu>
                <menuitem name="HistoryMenu" action="HistoryAction"/>
                <menu name="ProgMenu" action="ProgMenuAction">
                    <menuitem name="QuitMenu" action="QuitAction"/>
                    <menuitem name="QuitKillMenu" action="QuitKillAction"/>
                </menu>
            </menubar>
            <toolbar>
                <toolitem name="New" action="NewAction"/>
                <toolitem name="Reply" action="ReplyAction"/>
                <toolitem name="Cancel" action="CancelAction"/>
                <toolitem name="Supersede" action="SupsedeAction"/>
                <separator/>
                <toolitem name="ParentGoto" action="GotoParentAction"/>
                <toolitem name="Quit" action="QuitAction"/>
            </toolbar>
        </ui>
        """
    
        self.ui_manager = gtk.UIManager()
        self.ui_manager.add_ui_from_string(xml_source)
        self.action_group = gtk.ActionGroup("MainActions")
        self.action_group.add_actions([
            ("GrpMenuAction", None, "_Groupes", None, None, None),
            ("GrpGotoAction", None, "_Changer de groupe", "g",
             u"Aller dans un groupe donné", self.action_grpgoto_callback),
            ("SubscribeAction", None, u"_Gérer les abonnements", "L",
             u"Gérer les abonnements aux groupes",
             self.action_subscribe_callback),
            ("GrpSyncAction", None, u"_Rafraîchir la liste des groupes",
             None, u"Recharger la liste des groupes du serveur",
             self.action_syncgroups_callback),

            ("SumMenuAction", None, "_Sommaire", None, None, None),
            ("SumGotoAction", None, u"_Voir l'article numéro...", "v",
             u"Voir le n-ième article du groupe",
             self.action_sumgoto_callback),
            ("OverviewAction", None, u"Voir le sommai_re du groupe...", "r",
             u"Voir le sommaire du groupe...", self.action_overview_callback),
            ("NextUnreadAction", gtk.STOCK_GO_FORWARD, "Article sui_vant",
             "n", "Aller àu prochain article non lu",
             self.action_nextunread_callback),
            ("ZapRepliesAction", gtk.STOCK_MEDIA_FORWARD, 
             "Marquer la suite de la discussion comme lue", "<shift>K",
             "", self.action_killreplies_callback),
            ("ZapThreadAction", gtk.STOCK_CLEAR, 
             "Marquer la discussion comme lue", "<shift>J", "",
             self.action_killthread_callback),
            ("UnzapRepliesAction", gtk.STOCK_MEDIA_REWIND, 
             "Marquer la suite de la discussion comme non lue", "<ctrl><shift>K",
             "", self.action_unkillreplies_callback),
            ("UnzapThreadAction", gtk.STOCK_UNDELETE, 
             "Marquer la discussion comme non lue", "<ctrl><shift>J", "",
             self.action_unkillthread_callback),
            ("SaveTreeAsImageAction", None, "Exporter l'arbre...", None,
             "Enregistre l'arbre de la discussion dans une image", 
             self.action_savetreeasimage),
            
            ("ArtMenuAction", None, "_Articles", None, None, None),
            ("NewAction", gtk.STOCK_NEW, "_Nouveau message", "M",
             u"Écrire un nouveau message", self.action_new_callback),
            ("ReplyAction", gtk.STOCK_REDO, u"_Répondre", "<shift>R",
             u"Répondre à un message", self.action_reply_callback),
            ("CancelAction", gtk.STOCK_DELETE, "_Cancel", "e",
             u"Effacer un message (cancel)", self.action_cancel_callback),
            ("SupsedeAction", gtk.STOCK_STRIKETHROUGH, "_Supersede", None,
             u"Remplacer un message (supersede)",
             self.action_supsede_callback),
            ("GotoParentAction", gtk.STOCK_GO_UP, "Aller au _parent", "asciicircum", 
             u"Aller au message parent", self.action_goto_parent_callback),
            ("MsgidGotoAction", gtk.STOCK_JUMP_TO, u"Suivre le Ms_gId...",
             None, u"Voir un article donné par son Message-Id",
             self.action_msgidgoto_callback),
            ("MsgViewRawAction", None, u"_Voir un article brut", "<shift>V",
             u"Voir l'article brut (tel qu'il est sur le serveur)", 
             self.action_msgviewraw_callback),

            ("HistoryAction", None, "_Historique", "<shift>H",
             u"Voir l'historique des messages consultés",
             self.action_history_callback),

            ("ProgMenuAction", None, "_Programme", None, None, None),
            ("QuitAction", gtk.STOCK_QUIT, "_Quitter", "<control>Q",
             u"Quitter le programme", self.action_quit_callback),
            ("QuitKillAction", gtk.STOCK_STOP, "Quitter _sans sauver", 
             "<control><shift>Q", 
             u"Quitter le programme sans enregistrer les messages lus", 
             self.action_quit_kill_callback)])
        self.action_group.add_toggle_actions([
                ("MsgRot13Action", gtk.STOCK_SORT_ASCENDING, 
                 u"Transformée par _Rot13", "<shift>X", 
                 "Afficher le message en rot13", self.action_rot13ify_callback)])
        self.ui_manager.insert_action_group(self.action_group, 0)

        # Définitions pour la fenêtre principale
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title(self.conf.my_hdrs['User-Agent'])
        self.window.set_default_size(1000,700)
        self.window.connect("delete_event", self.action_quit_callback)
        self.window.add_accel_group(self.ui_manager.get_accel_group())

        # Boîte principale
        self.vbox_big = gtk.VBox()
        self.window.add(self.vbox_big)
        self.vbox_big.show()
            
        # Barre de boutons
        self.vbox_big.pack_start(
            self.ui_manager.get_widget("/ui/menubar"), False, False, 0)
        self.vbox_big.pack_start(
            self.ui_manager.get_widget("/ui/toolbar"), False, False, 0)
        self.vbox_big.show_all()

        # Panneau à contis
        self.panel_big = gtk.HPaned()
        self.vbox_big.pack_start(self.panel_big, True, True, 0)
        self.panel_big.show()
        self.group_tab = GroupBuffer(self, self.panel_big.pack1)
        self.group_tab.widget.get_selection().connect(
            "changed", self.select_group_callback)
