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

#include "nntp.hpp"

#ifdef DEBUG
#include <iostream>
#endif

#define DEFAULT_PORT 119

using namespace std;

NNTPConnection::NNTPConnection() {
}

void NNTPConnection::connect(Glib::ustring server) {
  client = Gio::SocketClient::create();
  client->set_socket_type(Gio::SOCKET_TYPE_STREAM);
#ifdef DEBUG
  cout << "Connecting to server " << server << endl;
#endif
  socket = client->connect_to_host(server, DEFAULT_PORT);
  sin = Gio::DataInputStream::create(socket->get_input_stream());
  sout = Gio::DataOutputStream::create(socket->get_output_stream());
  sin->set_newline_type(Gio::DATA_STREAM_NEWLINE_TYPE_CR_LF);

  // Read welcome message: respcode = 200 means posting is allowed
  int code = getresp();
  read_only = (code == 201) ? true : false;
}

NNTPConnection::NNTPConnection(Glib::ustring server) {
  connect(server);
}

NNTPConnection::~NNTPConnection() {
}

int NNTPConnection::getresp() {
  if (!socket) return 0;
  sin->read_line(buffer);
#ifdef DEBUG
  cout << buffer << endl;
#endif
  istringstream s(buffer);
  int code = 0;
  s >> code;
  return code;
}

list<string> NNTPConnection::getmultiline() {
  list<string> result;
  while (sin->read_line(buffer)) {
#ifdef DEBUG
    cout << buffer << endl;
#endif
    if ( buffer == "." ) break;
    // '..' is for escaping '.'
    if ( buffer.compare(0, 2, "..") == 0 ) buffer.erase(0, 1);
    result.push_back(buffer);
  }

  return result;
}

int NNTPConnection::groups_names(list<string> & groups) {
  sout->put_string("LIST\n");
  int code = getresp();
  if (code / 10 != 21) return 0;

  list<string> result = getmultiline();
  groups.clear();
  for (list<string>::iterator i = result.begin(); i != result.end(); i++)
    {
      string g;
      istringstream st(*i);
      st >> g;
      groups.push_back(g);
    }

  return 1;
}

int NNTPConnection::groups_info(list<group_entry> & groups) {
  sout->put_string("LIST\n");
  int code = getresp();
  if (code / 10 != 21) return 0;

  list<string> result = getmultiline();
  groups.clear();
  for (list<string>::iterator i = result.begin(); i != result.end(); i++)
    {
      group_entry g;
      istringstream st(*i);
      st >> g.name >> g.last >> g.first;
      groups.push_back(g);
    }

  return 1;
}

int NNTPConnection::group_info(std::string name, int & count, int & first, int & last) {
  sout->put_string("GROUP " + name + "\n");
  getresp();
  istringstream st(buffer);
  int code;
  count = first = last = 0;
  st >> code >> count >> first >> last;
  return code;
}

int NNTPConnection::overview(const string group, const int first, const int last,
			     list< list<string> > & result) {
  // Switch group
  sout->put_string("GROUP " + group + "\n");
  int code = getresp();
  if (code / 10 != 21) return code;
  // Ask for overview
  {
    ostringstream s;
    s << "XOVER " << first << "-" << last << endl;
    sout->put_string(s.str());
  }
  code = getresp();
  if (code / 10 != 22) return code;
  // Fill with results
  list<string> response = getmultiline();
  result.clear();
  for (list<string>::iterator i = response.begin();
       i != response.end(); i++) {
    list<string> item;
    size_t pos;
    string buf(*i);
    while ( !buf.empty() ) {
      // Slice into tokens
      pos = buf.find("\t");
      item.push_back(buf.substr(0, pos));
      buf.erase(0, pos); buf.erase(0,1);
    }

    result.push_back(item);
  }

  return code;
}
