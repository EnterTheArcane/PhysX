// SPDX-License-Identifier: Apache-2.0

#include <PxPhysicsAPI.h>
#include <foundation/PxVecMath.h>

static_assert(bool(PX_SUPPORT_GPU_PHYSX) == bool(EXPECT_GPU), "Unexpected GPU support");
#if defined(PX_PHYSX_STATIC_LIB) != EXPECT_STATIC
#error Unexpected static library definition
#endif
#if defined(_M_ARM64)
static_assert(PX_WINDOWS_FAMILY && PX_A64 && PX_NEON && COMPILE_VECTOR_INTRINSICS, "Expected Windows ARM NEON");
#endif

int main()
{
    physx::PxDefaultAllocator allocator;
    physx::PxDefaultErrorCallback errors;
    auto* foundation = PxCreateFoundation(PX_PHYSICS_VERSION, allocator, errors);
    if (!foundation) { return 1; }
    auto* physics = PxCreatePhysics(PX_PHYSICS_VERSION, *foundation, physx::PxTolerancesScale());
    if (!physics) { return 2; }
    const physx::PxVec3 vertices[] = {physx::PxVec3(0, 0, 0), physx::PxVec3(1, 0, 0), physx::PxVec3(0, 0, 1)};
    const physx::PxU32 indices[] = {0, 1, 2};
    physx::PxTriangleMeshDesc mesh;
    mesh.points.count = 3;
    mesh.points.stride = sizeof(physx::PxVec3);
    mesh.points.data = vertices;
    mesh.triangles.count = 1;
    mesh.triangles.stride = sizeof(indices);
    mesh.triangles.data = indices;
    physx::PxDefaultMemoryOutputStream cooked;
    if (!PxCookTriangleMesh(physx::PxCookingParams(physics->getTolerancesScale()), mesh, cooked)) { return 3; }
    auto* dispatcher = physx::PxDefaultCpuDispatcherCreate(1);
    physx::PxSceneDesc desc(physics->getTolerancesScale());
    desc.cpuDispatcher = dispatcher;
    desc.gravity = physx::PxVec3(0.0f, -9.81f, 0.0f);
    desc.filterShader = physx::PxDefaultSimulationFilterShader;
    auto* scene = physics->createScene(desc);
    if (!scene) { return 4; }

    auto* material = physics->createMaterial(0.5f, 0.5f, 0.0f);
    auto* body = physics->createRigidDynamic(physx::PxTransform(physx::PxIdentity));
    if (!material || !body) { return 5; }
    if (!physx::PxRigidActorExt::createExclusiveShape(*body, physx::PxSphereGeometry(0.5f), *material)) { return 6; }
    if (!physx::PxRigidBodyExt::updateMassAndInertia(*body, 1.0f)) { return 7; }
    scene->addActor(*body);
    scene->simulate(1.0f / 60.0f);
    const bool moved = scene->fetchResults(true) && body->getGlobalPose().p.y < 0.0f;
    physx::PxMemoryBarrier();
    body->release();
    material->release();
    scene->release();
    dispatcher->release();
    physics->release();
    foundation->release();
    if (!moved) { return 8; }
    return 0;
}
