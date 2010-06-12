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

#ifndef GRP_HIERARCHY_H
#define GRP_HIERARCHY_H

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <list>
#include <map>
#include <string>

class GrpHierarchy
{
public:
  GrpHierarchy();
  GrpHierarchy(std::list<std::string> groups);
  ~GrpHierarchy();

  void populate(std::list<std::string> groups);
  void insert(std::string key, std::string group);

  bool is_a_leaf;
  std::string name;

  // Iterators
  typedef std::map<std::string, GrpHierarchy>::iterator iter;
  iter begin() { return children.begin(); }
  iter end() { return children.end(); }

  bool has_child() { return !children.empty(); }
protected:
  std::map<std::string, GrpHierarchy> children;
};

#endif //!GRP_HIERARCHY_H
