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

#ifndef MAIN_WINDOW_H
#define MAIN_WINDOW_H

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <gtkmm.h>
#include <string>
#include "GrpBuffer.hpp"

class MainWindow : public Gtk::Window
{
public:
  MainWindow(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
  ~MainWindow() {};

protected:
  Glib::RefPtr<Gtk::Builder> uidef;
  GrpBuffer *grp_buffer;

  void connect_action(Glib::ustring name, void(MainWindow::*callback)()) {
      Glib::RefPtr<Gtk::Action> obj;
      obj = Glib::RefPtr<Gtk::Action>::cast_dynamic(uidef->get_object(name));
      obj->signal_activate().connect( sigc::mem_fun(*this, callback) );
  };

  void _on_grp_goto_activate() {};
  void _on_subscribe_activate() {};
  void _on_grp_sync_activate() {};

  void _on_sum_goto_activate() {};
  void _on_overview_activate() {};
  void _on_next_unread_activate() {};

  void _on_zap_replies_activate() {};
  void _on_zap_thread_activate() {};
  void _on_unzap_replies_activate() {};
  void _on_unzap_thread_activate() {};
  
  void _on_save_tree_activate() {};
  void _on_new_activate() {};
  void _on_reply_activate() {};
  void _on_cancel_activate() {};
  void _on_supsede_activate() {};

  void _on_goto_parent_activate() {};
  void _on_goto_msgid_activate() {};
  void _on_view_raw_activate() {};

  void _on_history_activate() {};

  void _on_quit_activate();
  void _on_quit_kill_activate();
};

#endif //!MAIN_WINDOW_H
