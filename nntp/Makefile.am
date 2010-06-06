noinst_LIBRARIES = libnntp.a

libnntp_a_SOURCES = \
	nntp.cpp nntp.hpp
libnntp_a_CPPFLAGS = $(GIOMM_CFLAGS)

check_PROGRAMS = test_nntp
test_nntp_SOURCES = test_nntp.cpp nntp.hpp
test_nntp_CPPFLAGS = -DDEBUG $(GIOMM_CFLAGS)
test_nntp_LDADD = libnntp.a $(GIOMM_LIBS)

