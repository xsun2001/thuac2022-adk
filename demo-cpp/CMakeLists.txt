cmake_minimum_required(VERSION 3.11)
project(cpp)

set(CMAKE_CXX_STANDARD 11)

if (ONLINE_JUDGE)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
endif ()

add_executable(main main.cpp)

if (WIN32)
    target_link_libraries(main PUBLIC ws2_32)
endif ()