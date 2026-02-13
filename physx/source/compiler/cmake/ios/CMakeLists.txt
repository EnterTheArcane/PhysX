## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions
## are met:
##  * Redistributions of source code must retain the above copyright
##    notice, this list of conditions and the following disclaimer.
##  * Redistributions in binary form must reproduce the above copyright
##    notice, this list of conditions and the following disclaimer in the
##    documentation and/or other materials provided with the distribution.
##  * Neither the name of NVIDIA CORPORATION nor the names of its
##    contributors may be used to endorse or promote products derived
##    from this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS `''AS IS'' AND ANY
## EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
## IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
## PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
## PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
## OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
##
## Copyright (c) 2008-2025 NVIDIA Corporation. All rights reserved.

STRING(TOLOWER "${CMAKE_BUILD_TYPE}" CMAKE_BUILD_TYPE_LOWERCASE)

SET(PHYSX_WARNING_DISABLES -Wno-invalid-noreturn -Wno-sometimes-uninitialized -Wno-missing-braces -Wno-unused-private-field -Wno-unused-local-typedef)

IF(CMAKE_BUILD_TYPE_LOWERCASE STREQUAL "debug")
SET(PHYSX_IOS_DEBUG_COMPILE_DEFS "PX_DEBUG=1;PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_CHECKED_COMPILE_DEFS "PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_PROFILE_COMPILE_DEFS "PX_PROFILE=1" CACHE INTERNAL "")
SET(PHYSX_IOS_RELEASE_COMPILE_DEFS "" CACHE INTERNAL "")
ELSEIF(CMAKE_BUILD_TYPE_LOWERCASE STREQUAL "checked")
SET(PHYSX_IOS_DEBUG_COMPILE_DEFS "PX_DEBUG=1;PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_CHECKED_COMPILE_DEFS "PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_PROFILE_COMPILE_DEFS "PX_PROFILE=1" CACHE INTERNAL "")
SET(PHYSX_IOS_RELEASE_COMPILE_DEFS "" CACHE INTERNAL "")
ELSEIF(CMAKE_BUILD_TYPE_LOWERCASE STREQUAL "profile")
SET(PHYSX_IOS_DEBUG_COMPILE_DEFS "PX_DEBUG=1;PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_CHECKED_COMPILE_DEFS "PX_CHECKED=1" CACHE INTERNAL "")
SET(PHYSX_IOS_PROFILE_COMPILE_DEFS "PX_PROFILE=1" CACHE INTERNAL "")
SET(PHYSX_IOS_RELEASE_COMPILE_DEFS "" CACHE INTERNAL "")
ELSEIF(CMAKE_BUILD_TYPE_LOWERCASE STREQUAL "release")
SET(PHYSX_IOS_DEBUG_COMPILE_DEFS "" CACHE INTERNAL "")
SET(PHYSX_IOS_CHECKED_COMPILE_DEFS "" CACHE INTERNAL "")
SET(PHYSX_IOS_PROFILE_COMPILE_DEFS "" CACHE INTERNAL "")
SET(PHYSX_IOS_RELEASE_COMPILE_DEFS "" CACHE INTERNAL "")
ENDIF()

SET(PHYSX_IOS_COMPILE_DEFS DISABLE_CUDA_PHYSX;${PHYSX_LIBTYPE_DEFS};PX_SUPPORT_OMNI_PVD=0 CACHE INTERNAL "")

# Include all the per-library cmake files
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/LowLevel.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/LowLevelAABB.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/LowLevelDynamics.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysX.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXCharacterKinematic.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXCommon.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXCooking.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXExtensions.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXFoundation.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXPvdSDK.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXTask.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/PhysXVehicle.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/SceneQuery.cmake)
INCLUDE(${PHYSX_ROOT_DIR}/source/compiler/cmake/ios/SimulationController.cmake)

# Set the target platform for distribution
SET(PHYSX_PLATFORM_INSTALL_PREFIX bin/ios.arm64)

# Distribution - install static libraries
INSTALL(DIRECTORY ${PHYSX_ROOT_DIR}/include/ DESTINATION include)
