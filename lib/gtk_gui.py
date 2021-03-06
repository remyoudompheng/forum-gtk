# -*- coding: utf-8 -*-

# Flrn-gtk: fenêtre principale
# Rémy Oudompheng, 2005-2006

# Modules GTK
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk

# Modules
from grp_buffer import GroupBuffer
from sum_buffer import SummaryBuffer
from art_buffer import ArticleBuffer
from tree_buffer import TreeBuffer
import main_window

class MainWindow (main_window.SkelMainWindow):
    def action_savetreeasimage(self, action):
        dialog = gtk.FileChooserDialog(
            "Enregistrer l'arbre sous...",
            self.window, gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_SAVE, gtk.RESPONSE_OK,
             gtk.STOCK_CLOSE, gtk.RESPONSE_DELETE_EVENT))
        dialog.set_current_name("tree.png")
        if (dialog.run() == gtk.RESPONSE_OK):
            name = dialog.get_filename()
            self.tree_tab.surface.write_to_png(name)
        dialog.destroy()
        
    def __init__(self, conf_source):
        self.init_common(conf_source)

        # Quelques cadres
        self.panel_right = gtk.VPaned()
        self.panel_big.pack2(self.panel_right)
        self.panel_big.set_property("position", 250)
        self.panel_right.show()
        # De quoi mémoriser l'emplacement des choses
        self.panel_right.connect("notify::position",
                                 main_window.remember_sep_height_callback)

        if self.conf.params['small_tree']:
            # Arbre du thread et sommaire
            self.panel_topright = gtk.HPaned()
            self.panel_right.pack1(self.panel_topright)
            self.panel_topright.show()
            
            self.summary_tab = SummaryBuffer(self.panel_topright.pack1, self)
            self.tree_tab = TreeBuffer(self, self.panel_topright.pack2)
            self.summary_tab.data.connect(
                "row-changed", self.summary_tab.changed_tree_callback)
        else:
            # Juste le sommaire
            self.summary_tab = SummaryBuffer(self.panel_right.pack1, self)

        # Panneau d'affichage de l'article
        self.article_tab = ArticleBuffer(
            None, False, self.panel_right.pack2, self)
        
        # Barre d'état
        self.status_bar = gtk.Statusbar()
        self.vbox_big.pack_start(self.status_bar, False, False, 0)
        self.status_bar.show()

        self.window.show()

        # Variables d'état
        self.current_group = None
        self.current_article = None
        self.history = []

        # Initialisation des affichages
        self.group_tab.display_tree(False)
