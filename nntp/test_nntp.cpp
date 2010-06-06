#include "nntp.hpp"
#include <iostream>

using namespace std;

int main(int argc, char *argv[])
{
  Glib::init();
  Gio::init();

  NNTPConnection server("localhost:1776");

  list<group_entry> g;
  server.groups_list(g);

  for(list<group_entry>::iterator i = g.begin(); i != g.end(); i++)
    {
      cout << "Group : " << i->name;
      cout << " (" << i->first << "-" << i->last << ")" << endl;
    }
  
  int c, f, l;
  server.group_info("junk", c, f, l);
  cout << "Info junk : " << c << f << l << endl;
  return 0;
}
