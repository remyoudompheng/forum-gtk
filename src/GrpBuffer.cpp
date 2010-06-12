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

#include "GrpBuffer.hpp"

#ifdef DEBUG
#include <iostream>
#endif

using namespace std;

GrpBuffer::GrpBuffer(BaseObjectType* cobject,
		     const Glib::RefPtr<Gtk::Builder>& refGlade)
  : Gtk::TreeView(cobject),
    uidef(refGlade)
{
  columns = new GrpColumns();
  data = Gtk::TreeStore::create(*columns);
  set_model(data);
}

void GrpBuffer::fill_tree(list<string> groups)
{
  data->clear();
  for(list<string>::iterator i = groups.begin();
      i != groups.end(); i++)
    {
      Gtk::TreeIter it;
      it = data->append();
      (*it)[columns->name] = *i;
      (*it)[columns->caption] = *i;
      (*it)[columns->subscribed] = false;
      (*it)[columns->internal] = false;
      (*it)[columns->font] = "normal";
    }
}

void GrpBuffer::fill_tree_branch(Gtk::TreeIter node, GrpHierarchy groups)
{
  for(GrpHierarchy::iter i = groups.begin();
      i != groups.end(); i++)
    {
      Gtk::TreeIter it;
      it = data->append(node->children());
      (*it)[columns->name] = i->second.name;
      (*it)[columns->subscribed] = false;
      (*it)[columns->font] = "normal";
      if (i->second.name.empty()) {
	(*it)[columns->internal] = true;
	(*it)[columns->caption] = i->first;
      } else {
	(*it)[columns->internal] = false;
	(*it)[columns->caption] = i->second.name;
      }

      if (i->second.has_child())
	fill_tree_branch(it, i->second);
    }
}

void GrpBuffer::fill_tree(GrpHierarchy groups)
{
  data->clear();
  for(GrpHierarchy::iter i = groups.begin();
      i != groups.end(); i++)
    {
      Gtk::TreeIter it;
      it = data->append();
      (*it)[columns->name] = i->second.name;
      (*it)[columns->subscribed] = false;
      (*it)[columns->font] = "normal";
      if (i->second.name.empty()) {
	// No group name; this is an internal node
	(*it)[columns->internal] = true;
	(*it)[columns->caption] = i->first;
      } else {
	(*it)[columns->internal] = false;
	(*it)[columns->caption] = i->second.name;
      }

#ifdef DEBUG
      cout << "Key : " << i->first << ", group " << i->second.name << endl;
#endif

      if (i->second.has_child())
	fill_tree_branch(it, i->second);
    }
}
