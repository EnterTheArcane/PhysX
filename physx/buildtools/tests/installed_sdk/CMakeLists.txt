# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.21)
project(PhysXConsumer LANGUAGES CXX)

find_package(PhysX 5.13.0 EXACT CONFIG REQUIRED)

if(EXPECT_GPU)
    if(NOT TARGET PhysX::PhysXGpu)
        message(FATAL_ERROR "GPU runtime missing from combined SDK")
    endif()
    file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/gpu-path.txt" CONTENT "$<TARGET_FILE:PhysX::PhysXGpu>")
elseif(TARGET PhysX::PhysXGpu)
    message(FATAL_ERROR "CPU-only SDK unexpectedly exports a GPU runtime")
endif()

get_target_property(physx_dependencies PhysX::physx_lib INTERFACE_LINK_LIBRARIES)
if(physx_dependencies MATCHES "PhysXGpu|CUDA::")
    message(FATAL_ERROR "CPU consumer depends on the GPU runtime")
endif()

add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE PhysX::physx_lib)
set_property(TARGET consumer PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
target_compile_definitions(consumer PRIVATE
    "$<$<CONFIG:Debug>:_DEBUG>"
    "$<$<NOT:$<CONFIG:Debug>>:NDEBUG>"
    EXPECT_GPU=$<BOOL:${EXPECT_GPU}>
    EXPECT_STATIC=$<BOOL:${EXPECT_STATIC}>
)
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set_target_properties(consumer PROPERTIES MACOSX_BUNDLE TRUE)
endif()
file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/exe-$<CONFIG>.txt" CONTENT "$<TARGET_FILE:consumer>")
