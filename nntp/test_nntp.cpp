#include "nntp.hpp"
#include <iostream>

using namespace std;

int main(int argc, char *argv[])
{
  Glib::init();
  Gio::init();

  NNTPConnection server("localhost:1776");

  list<group_entry> g;
  server.groups_info(g);

  for(list<group_entry>::iterator i = g.begin(); i != g.end(); i++)
    {
      cout << "Group : " << i->name;
      cout << " (" << i->first << "-" << i->last << ")" << endl;
    }
  
  int c, f, l;
  server.group_info("junk", c, f, l);
  cout << "Info junk : " << c << f << l << endl;

  list<list<string> > overview;
  int code = server.overview("control", 10, 20, overview);
  cout << code << endl;
  for(list<list<string> >::iterator i = overview.begin();
      i != overview.end(); i++) {
    for(list<string>::iterator j = i->begin(); j != i->end(); j++)
      cout << *j << endl;
    cout << endl;
  }

  return 0;
}
