include_directories(
    ${CMAKE_SOURCE_DIR}/nntp
    ${CMAKE_SOURCE_DIR}/util
    ${GTKMM_INCLUDE_DIRS} ${CMAKE_CURRENT_BINARY_DIR})
link_directories(
    ${CMAKE_BINARY_DIR}/nntp
    ${CMAKE_BINARY_DIR}/util
    ${GTKMM_LIBRARY_DIRS})

add_executable(forum_gtk
      main.cpp 
      MainWindow.cpp MainWindow.hpp
      GrpBuffer.cpp GrpBuffer.hpp)
target_link_libraries(forum_gtk nntp utiltypes ${GTKMM_LIBRARIES})

install(TARGETS forum_gtk RUNTIME DESTINATION bin)

