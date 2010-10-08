cmake_minimum_required(VERSION 2.6)

PROJECT(forum-gtk)

Include(FindPkgConfig)
pkg_check_modules(GTK2 REQUIRED gtk+-2.0>=2.16)
pkg_check_modules(GLIBMM REQUIRED glibmm-2.4>=2.24)
pkg_check_modules(GIOMM REQUIRED giomm-2.4>=2.24)
pkg_check_modules(GTKMM gtkmm-2.4>=2.16)

add_subdirectory(util)
add_subdirectory(nntp)
add_subdirectory(share)
add_subdirectory(src)

