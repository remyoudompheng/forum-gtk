/*
 * forum-gtk
 * A minimalistic newsreader
 *
 * Copyright (C) 2010 Rémy Oudompheng

 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "MainWindow.hpp"

MainWindow::MainWindow(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade)
  : Gtk::Window(cobject),
    uidef(refGlade)
{
  // Connect actions to callbacks
  connect_action("act_grpgoto", &MainWindow::_on_grp_goto_activate);
  connect_action("act_grpgoto", &MainWindow::_on_grp_goto_activate);
  connect_action("act_subscribe", &MainWindow::_on_subscribe_activate);
  connect_action("act_grpsync", &MainWindow::_on_grp_sync_activate);
  
  connect_action("act_sumgoto", &MainWindow::_on_sum_goto_activate);
  connect_action("act_overview", &MainWindow::_on_overview_activate);
  connect_action("act_nextunread", &MainWindow::_on_next_unread_activate);

  connect_action("act_zapreplies", &MainWindow::_on_zap_replies_activate);
  connect_action("act_zapthread", &MainWindow::_on_zap_thread_activate);
  connect_action("act_unzapreplies", &MainWindow::_on_unzap_replies_activate);
  connect_action("act_unzapthread", &MainWindow::_on_unzap_thread_activate);

  connect_action("act_savetree", &MainWindow::_on_save_tree_activate);

  connect_action("act_new", &MainWindow::_on_new_activate);
  connect_action("act_reply", &MainWindow::_on_reply_activate);
  connect_action("act_cancel", &MainWindow::_on_cancel_activate);
  connect_action("act_supsede", &MainWindow::_on_supsede_activate);

  connect_action("act_gotoparent", &MainWindow::_on_goto_parent_activate);
  connect_action("act_msgidgoto", &MainWindow::_on_goto_msgid_activate);
  connect_action("act_msgviewraw", &MainWindow::_on_view_raw_activate);
  
  connect_action("act_history", &MainWindow::_on_history_activate);

  connect_action("act_quit", &MainWindow::_on_quit_activate);
  connect_action("act_quitkill", &MainWindow::_on_quit_kill_activate);

  uidef->get_widget_derived("tree_groups", grp_buffer);

  show_all();
}

// Action callbacks
void MainWindow::_on_quit_activate() {
  hide_all();
  Gtk::Main::quit();
}

void MainWindow::_on_quit_kill_activate() {
  hide_all();
  Gtk::Main::quit();
}
