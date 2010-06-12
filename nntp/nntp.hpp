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

#ifndef NNTP_H
#define NNTP_H

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <giomm.h>

typedef struct {
  std::string name;
  int first;
  int last;
} group_entry;

class NNTPConnection
{
public:
  NNTPConnection();
  NNTPConnection(Glib::ustring server);
  ~NNTPConnection();

  bool read_only;

  void connect(Glib::ustring server);
  int groups_names(std::list<std::string> & groups);
  int groups_info(std::list<group_entry> & groups);
  int group_info(std::string name, int & count, int & first, int & last);

protected:
  Glib::ustring server;
  Glib::RefPtr<Gio::SocketClient> client;
  Glib::RefPtr<Gio::SocketConnection> socket;
  Glib::RefPtr<Gio::DataInputStream> sin;
  Glib::RefPtr<Gio::DataOutputStream> sout;

  std::string buffer;

  int getresp();
  std::list<std::string> getmultiline();
};

#endif //!NNTP_H
