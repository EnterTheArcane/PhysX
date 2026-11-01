# Copyright (c) Contributors to the Open 3D Engine Project.
# SPDX-License-Identifier: Apache-2.0 OR MIT
cmake_minimum_required(VERSION 3.25)
project(BlastRuntimeConsumer LANGUAGES CXX)
set(CMAKE_CONFIGURATION_TYPES "Debug;Checked;Profile;Release" CACHE STRING "Build configurations" FORCE)
# The installed target SDK lives outside the compiler's system sysroot.
list(APPEND CMAKE_FIND_ROOT_PATH ${CMAKE_PREFIX_PATH})
find_package(Blast CONFIG REQUIRED)
add_executable(blast-runtime main.cpp)
target_link_libraries(blast-runtime PRIVATE
    Blast::NvBlastExtAssetUtils Blast::NvBlastExtShaders Blast::NvBlastExtStress Blast::NvBlastExtTkSerialization)
target_compile_definitions(blast-runtime PRIVATE
    EXPECT_ANDROID=$<BOOL:${ANDROID}>
    EXPECT_IOS=$<STREQUAL:${CMAKE_SYSTEM_NAME},iOS>
    EXPECT_MAC=$<STREQUAL:${CMAKE_SYSTEM_NAME},Darwin>)
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set_target_properties(blast-runtime PROPERTIES MACOSX_BUNDLE TRUE)
endif()
if(WIN32 AND EXISTS "${Blast_DIR}/../../../bin")
    add_custom_command(TARGET blast-runtime POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory "${Blast_DIR}/../../../bin" "$<TARGET_FILE_DIR:blast-runtime>"
        VERBATIM)
endif()
file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/consumer-$<CONFIG>.txt" CONTENT "$<TARGET_FILE:blast-runtime>\n")
enable_testing()
add_test(NAME BlastRuntime COMMAND blast-runtime)
