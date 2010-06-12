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

#include "GrpHierarchy.hpp"

using namespace std;

GrpHierarchy::GrpHierarchy() {}
GrpHierarchy::~GrpHierarchy() {}

GrpHierarchy::GrpHierarchy(list<string> groups) {
  populate(groups);
}

void GrpHierarchy::populate(list<string> groups) {
  for(list<string>::iterator i = groups.begin();
      i != groups.end(); i++)
    insert(*i, *i);
}

void GrpHierarchy::insert(string key, string group) {
  size_t dot;
  dot = key.find_first_of(".");

  string prefix = key.substr(0, dot);
  string suffix = key.substr(dot+1);

  iter child = children.find(prefix);
  if(child == children.end()) {
    // Create a child if it does not exist
    children[prefix].name.clear();
    child = children.find(prefix);
  }
  
  if (dot == string::npos) {
    // There is no dot, it is a real group
    child->second.name = group;
  } else {
    // There was a dot, insert group in the child
    child->second.insert( suffix, group );
  }
}
