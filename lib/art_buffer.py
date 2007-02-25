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

class ArticleBuffer:
    def desusurpation(self, article):
        """En cas d'usurpation"""
        if 'Sender' in article.headers:
            real_login = article.headers['Sender'].strip().split('@')[0]
            from_login = email.Utils.parseaddr(
                article.headers['From'].strip())[1].split('@')[0]
            if from_login != real_login:
                return article.headers['From'] + ' [' + real_login + ']'
            else:
                return article.headers['From']
        else:
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
                    textbuf.insert_with_tags_by_name(
                        iter, u'Réponse à: ', "head_name")
                    textbuf.insert_with_tags_by_name(
                        iter, self.desusurpation(father) + '\n', "head_content")
            return
        if header not in article.headers:
            return
        if header == 'From':
            # Pour le From, on précise le Sender si nécessaire
            textbuf.insert_with_tags_by_name(iter, 'From: ', "head_name")
            textbuf.insert_with_tags_by_name(
                iter, self.desusurpation(article) + '\n', "head_content")
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

            # La photo annuaire
            try:
                login = article.headers['Sender'].strip().split('@')[0]
                self.face_head.set_from_pixbuf(
                    gtk.gdk.pixbuf_new_from_file_at_size(
                    os.path.expanduser("~annuaire/www/htdocs/photos/petit/%s.jpg" % login),
                    64, -1))
            except:
                self.face_head.clear()

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
            self.container.pack2(self.scrolled, True)
            self.scrolled.show()
            
            self.scrolled.add(self.widget)
            self.widget.show()
            # Zone d'affichage des en-t€tes
            self.pane_head = gtk.HPaned()
            self.container.pack1(self.pane_head, False)
            self.scrolled_head = gtk.ScrolledWindow()
            self.scrolled_head.set_policy(gtk.POLICY_AUTOMATIC,
                                          gtk.POLICY_AUTOMATIC)

            self.buffer_head = gtk.TextBuffer(self.parent.conf.tagtable)
            self.widget_head = gtk.TextView(self.buffer_head)
            self.widget_head.set_property("editable", False)
            self.widget_head.modify_font(pango.FontDescription("monospace"))
            self.widget_head.set_wrap_mode(gtk.WRAP_WORD)
            self.scrolled_head.add(self.widget_head)
            self.pane_head.pack1(self.scrolled_head, True)
            self.face_head = gtk.Image()
            self.pane_head.pack2(self.face_head, False)
            self.pane_head.show_all()

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
        
