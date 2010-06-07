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

#ifndef GRP_BUFFER_H
#define GRP_BUFFER_H

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <gtkmm.h>
#include <list>

class GrpBuffer : public Gtk::TreeView
{
public:
  GrpBuffer(BaseObjectType* cobject, const Glib::RefPtr<Gtk::Builder>& refGlade);
  ~GrpBuffer() {};

  void fill_tree(std::list<std::string> groups);

protected:
  class GrpColumns : public Gtk::TreeModel::ColumnRecord
  {
  public:
    GrpColumns() {
      add(name); add(caption);
      add(subscribed); add(internal);
      add(font);
    }

    Gtk::TreeModelColumn<Glib::ustring> name;    // 0
    Gtk::TreeModelColumn<Glib::ustring> caption; // 1
    Gtk::TreeModelColumn<bool> subscribed;       // 2
    Gtk::TreeModelColumn<bool> internal;         // 3
    Gtk::TreeModelColumn<Glib::ustring> font;    // 4
  };

  Glib::RefPtr<Gtk::Builder> uidef;
  Glib::RefPtr<Gtk::TreeStore> data;
  GrpColumns *columns;
};

#endif //!TREE_BUFFER_H
