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

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <gtkmm.h>
#include "guibuilder.h"

#include "MainWindow.hpp"

#include <getopt.h>

#include <iostream>
#include <string>
#include <cassert>
using namespace std;

string notice = PACKAGE_STRING "\n"
  "Copyright (C) 2006-2010 Rémy Oudompheng\n"
  "This program comes with ABSOLUTELY NO WARRANTY.\n"
  "This is free software, and you are welcome to redistribute it\n"
  "under certain conditions. See COPYING file for details.\n";

int
main (int argc, char *argv[])
{
  // Options
  static option longopts[] = {
    { "library", 1, 0, 'd' },
    { "version", no_argument, 0, 'V' },
    {0, 0, 0, 0}
  };
  char c;
  string library_dir = "";
  c = getopt_long(argc, argv, "d:V", longopts, &optind);

  switch(c) {
  }

  Gtk::Main kit(argc, argv);
  Glib::ustring guidef(gui_xml, gui_xml_len);
  Glib::RefPtr<Gtk::Builder> refGlade = Gtk::Builder::create();
  bool ok = refGlade->add_from_string(guidef);
  assert(ok);

  MainWindow *window_main;
  refGlade->get_widget_derived("window_main", window_main);
  if (window_main) {
    kit.run(*window_main);
  }

  delete window_main;

  return 0;
}
