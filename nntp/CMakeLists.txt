include_directories(${GIOMM_INCLUDE_DIRS})
link_directories(${GIOMM_LIBRARY_DIRS})

add_library(nntp STATIC
            nntp.cpp nntp.hpp)
target_link_libraries(nntp ${GIOMM_LIBRARIES})

add_executable(test_nntp test_nntp.cpp nntp.hpp)
target_link_libraries(test_nntp nntp ${GIOMM_LIBRARIES})
