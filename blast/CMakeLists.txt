# Copyright (c) Contributors to the Open 3D Engine Project.
# SPDX-License-Identifier: Apache-2.0 OR MIT

cmake_minimum_required(VERSION 3.25)
project(Blast VERSION 5.0.6 LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(FetchContent)
option(BUILD_SHARED_LIBS "Build shared runtime libraries" OFF)
option(BLAST_BUILD_HOST_TOOLS "Build the native Cap'n Proto schema compiler only" OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
set(CMAKE_CONFIGURATION_TYPES "Debug;Checked;Profile;Release" CACHE STRING "Build configurations" FORCE)
foreach(config CHECKED PROFILE)
    set(CMAKE_CXX_FLAGS_${config} "${CMAKE_CXX_FLAGS_RELWITHDEBINFO}" CACHE STRING "Compiler flags" FORCE)
    set(CMAKE_EXE_LINKER_FLAGS_${config} "${CMAKE_EXE_LINKER_FLAGS_RELWITHDEBINFO}" CACHE STRING "Linker flags" FORCE)
    set(CMAKE_SHARED_LINKER_FLAGS_${config} "${CMAKE_SHARED_LINKER_FLAGS_RELWITHDEBINFO}" CACHE STRING "Linker flags" FORCE)
endforeach()

# The runtime and the host generator must use the same schema compiler version.
FetchContent_Declare(capnproto
    URL https://capnproto.org/capnproto-c++-1.5.0.tar.gz
    URL_HASH SHA256=77dbc13ca82d9c87ddb4581dd49559d45b63096433d3dadea08b7f31b360a5ba)
block()
    set(BUILD_SHARED_LIBS OFF)
    set(BUILD_TESTING OFF)
    set(WITH_OPENSSL OFF CACHE STRING "" FORCE)
    set(WITH_ZLIB OFF CACHE STRING "" FORCE)
    set(WITH_FIBERS OFF CACHE STRING "" FORCE)
    set(CAPNP_LITE ON CACHE BOOL "Build only the serialization runtime" FORCE)
    if(BLAST_BUILD_HOST_TOOLS)
        set(CAPNP_LITE OFF CACHE BOOL "Build the native schema compiler" FORCE)
    endif()
    FetchContent_MakeAvailable(capnproto)
endblock()
FetchContent_GetProperties(capnproto)
if(BLAST_BUILD_HOST_TOOLS)
    file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/tools-$<CONFIG>.txt"
        CONTENT "$<TARGET_FILE:capnp_tool>\n$<TARGET_FILE:capnpc_cpp>\n")
    return()
endif()
# Cap'n Proto 1.5's lite mutex implementation also needs its clock implementation.
target_sources(kj PRIVATE "${capnproto_SOURCE_DIR}/src/kj/time.c++")
set_target_properties(kj capnp PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)

find_program(BLAST_CAPNP_EXECUTABLE NAMES capnp DOC "Native Cap'n Proto compiler" REQUIRED)
find_program(BLAST_CAPNPC_CXX_EXECUTABLE NAMES capnpc-c++ DOC "Native Cap'n Proto C++ plugin" REQUIRED)
set(serialization "${CMAKE_CURRENT_SOURCE_DIR}/source/sdk/extensions/serialization")
set(generated "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY "${generated}")
foreach(schema NvBlastExtLlSerialization-capn NvBlastExtTkSerialization-capn)
    add_custom_command(OUTPUT "${generated}/${schema}.c++" "${generated}/${schema}.h"
        COMMAND "${BLAST_CAPNP_EXECUTABLE}" compile
            -o "${BLAST_CAPNPC_CXX_EXECUTABLE}:${generated}"
            -I "${capnproto_SOURCE_DIR}/src" --src-prefix "${serialization}" "${serialization}/${schema}"
        DEPENDS "${serialization}/${schema}" "${serialization}/NvBlastExtLlSerialization-capn"
        VERBATIM)
endforeach()
add_custom_target(BlastSchemas DEPENDS
    "${generated}/NvBlastExtLlSerialization-capn.h" "${generated}/NvBlastExtTkSerialization-capn.h")

set(runtime_modules lowlevel globals toolkit extensions/assetutils extensions/shaders extensions/stress extensions/serialization)
set(runtime_includes include/shared/NvFoundation)
foreach(module IN LISTS runtime_modules)
    list(APPEND runtime_includes "include/${module}")
endforeach()
file(GLOB common CONFIGURE_DEPENDS source/sdk/common/*.cpp)
function(blast_runtime target module)
    set(sources ${ARGN})
    if(NOT sources)
        file(GLOB sources CONFIGURE_DEPENDS "source/sdk/${module}/*.cpp")
    endif()
    add_library(${target} ${sources} ${common})
    add_library(Blast::${target} ALIAS ${target})
    set_target_properties(${target} PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
    target_compile_features(${target} PUBLIC cxx_std_17)
    target_compile_definitions(${target} PUBLIC
        $<$<CONFIG:Debug>:_DEBUG;NV_DEBUG=1;NV_CHECKED=1>
        $<$<NOT:$<CONFIG:Debug>>:NDEBUG>
        $<$<CONFIG:Checked>:NV_CHECKED=1>
        $<$<CONFIG:Profile>:NV_PROFILE=1>)
    target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
    if(NOT BUILD_SHARED_LIBS)
        target_compile_definitions(${target} PUBLIC NV_FOUNDATION_DLL=0)
    elseif(target STREQUAL "NvBlastGlobals")
        target_compile_definitions(${target} PRIVATE NV_FOUNDATION_DLL=1)
    else()
        target_compile_definitions(${target} PRIVATE NV_FOUNDATION_DLL=0)
    endif()
    target_include_directories(${target} PRIVATE
        source/sdk/common "source/sdk/${module}" source/sdk/globals source/sdk/lowlevel
        source/shared/NsFoundation/include source/shared/NsFileBuffer/include source/shared/NvTask/include)
    foreach(directory IN LISTS runtime_includes)
        target_include_directories(${target} PUBLIC
            "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/${directory}>"
            "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/blast/${directory}>")
    endforeach()
    if(MSVC)
        target_compile_options(${target} PRIVATE /bigobj)
    endif()
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS" AND BUILD_SHARED_LIBS)
        set_target_properties(${target} PROPERTIES FRAMEWORK TRUE
            MACOSX_FRAMEWORK_IDENTIFIER "org.o3de.${target}"
            VERSION "${PROJECT_VERSION}"
            MACOSX_FRAMEWORK_BUNDLE_VERSION "${PROJECT_VERSION}"
            MACOSX_FRAMEWORK_SHORT_VERSION_STRING "${PROJECT_VERSION}")
    elseif(UNIX AND NOT APPLE)
        set_target_properties(${target} PROPERTIES INSTALL_RPATH "$ORIGIN")
    endif()
    if(NOT target STREQUAL "NvBlast" AND NOT target STREQUAL "NvBlastGlobals")
        target_link_libraries(${target} PUBLIC NvBlast NvBlastGlobals)
    endif()
    install(TARGETS ${target} EXPORT BlastTargets
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        FRAMEWORK DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endfunction()

blast_runtime(NvBlast lowlevel)
blast_runtime(NvBlastGlobals globals)
blast_runtime(NvBlastTk toolkit)
blast_runtime(NvBlastExtAssetUtils extensions/assetutils)
blast_runtime(NvBlastExtShaders extensions/shaders)
blast_runtime(NvBlastExtStress extensions/stress)
target_sources(NvBlastExtStress PRIVATE source/shared/stress_solver/stress.cpp)
if(WIN32)
    target_link_libraries(NvBlastTk PRIVATE Rpcrt4)
endif()
target_include_directories(NvBlastExtStress PRIVATE source/shared/stress_solver)
if(CMAKE_OSX_ARCHITECTURES STREQUAL "x86_64" OR
   (NOT APPLE AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64|x64)$"))
    if(MSVC)
        set_source_files_properties(source/shared/stress_solver/stress.cpp PROPERTIES COMPILE_OPTIONS /arch:AVX2)
    else()
        set_source_files_properties(source/shared/stress_solver/stress.cpp PROPERTIES COMPILE_OPTIONS "-mavx;-mfma")
    endif()
endif()

set(dto "${serialization}/DTO")
set(shared_dto "${dto}/AssetDTO.cpp" "${dto}/NvBlastChunkDTO.cpp" "${dto}/NvBlastBondDTO.cpp" "${dto}/NvBlastIDDTO.cpp")
set(streams "${serialization}/NvBlastExtOutputStream.cpp" "${serialization}/NvBlastExtInputStream.cpp")
blast_runtime(NvBlastExtSerialization extensions/serialization
    ${streams} ${shared_dto}
    "${serialization}/NvBlastExtSerialization.cpp" "${serialization}/NvBlastExtLlSerialization.cpp"
    "${dto}/ActorDTO.cpp" "${dto}/FamilyDTO.cpp" "${dto}/FamilyGraphDTO.cpp"
    "${generated}/NvBlastExtLlSerialization-capn.c++")
blast_runtime(NvBlastExtTkSerialization extensions/serialization
    ${streams} ${shared_dto}
    "${serialization}/NvBlastExtTkSerialization.cpp" "${serialization}/NvBlastExtTkSerializerRAW.cpp"
    "${dto}/TkAssetDTO.cpp" "${dto}/NvVec3DTO.cpp" "${dto}/TkAssetJointDescDTO.cpp"
    "${generated}/NvBlastExtLlSerialization-capn.c++" "${generated}/NvBlastExtTkSerialization-capn.c++")
foreach(target NvBlastExtSerialization NvBlastExtTkSerialization)
    add_dependencies(${target} BlastSchemas)
    target_include_directories(${target} PRIVATE "${dto}" "${generated}")
    target_link_libraries(${target} PRIVATE CapnProto::capnp)
endforeach()
target_link_libraries(NvBlastExtTkSerialization PUBLIC NvBlastTk NvBlastExtSerialization)

foreach(directory IN LISTS runtime_includes)
    install(DIRECTORY "${directory}/" DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/blast/${directory}")
endforeach()
install(EXPORT BlastTargets NAMESPACE Blast:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Blast)
configure_package_config_file(cmake/BlastConfig.cmake.in "${CMAKE_CURRENT_BINARY_DIR}/BlastConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Blast)
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/BlastConfigVersion.cmake" COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/BlastConfig.cmake" "${CMAKE_CURRENT_BINARY_DIR}/BlastConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Blast)
install(DIRECTORY PACKAGE-LICENSES/ DESTINATION ${CMAKE_INSTALL_DATADIR}/Blast/licenses)
install(FILES "${capnproto_SOURCE_DIR}/LICENSE.txt" DESTINATION ${CMAKE_INSTALL_DATADIR}/Blast/licenses RENAME capnproto-LICENSE.txt)
