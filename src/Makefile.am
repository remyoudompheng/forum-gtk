bin_PROGRAMS = forum-gtk

EXTRA_DIST = gui.xml

guibuilder.h: gui.xml
	$(XXD) -i gui.xml | $(SED) -e 's/unsigned char/const char/' > guibuilder.h
main.cpp: guibuilder.h

forum_gtk_SOURCES = main.cpp guibuilder.h \
	MainWindow.cpp MainWindow.hpp \
	GrpBuffer.cpp GrpBuffer.hpp

forum_gtk_CPPFLAGS = $(GTKMM_CFLAGS) -I../nntp -I../util

forum_gtk_LDADD = \
	../nntp/libnntp.a \
	../util/libutiltypes.a \
	$(GTKMM_LIBS)

clean-local:
	rm -f guibuilder.h
