// Copyright (c) Contributors to the Open 3D Engine Project.
// SPDX-License-Identifier: Apache-2.0 OR MIT

#include <NvBlast.h>
#include <NvBlastExtAssetUtils.h>
#include <NvBlastExtDamageShaders.h>
#include <NvBlastExtLlSerialization.h>
#include <NvBlastExtSerialization.h>
#include <NvBlastExtStressSolver.h>
#include <NvBlastExtTkSerialization.h>
#include <NvBlastTkFramework.h>
#include <NvAssert.h>
#include <cstdio>

static_assert(bool(NV_ANDROID) == bool(EXPECT_ANDROID), "Android platform detection failed");
static_assert(bool(NV_IOS) == bool(EXPECT_IOS), "iOS platform detection failed");
static_assert(bool(NV_OSX) == bool(EXPECT_MAC), "Mac platform detection failed");

#define CHECK(expression) \
    if (!(expression)) { std::fprintf(stderr, "Failed: %s\n", #expression); return 1; }

class CountingAssertHandler : public nvidia::NvAssertHandler
{
public:
    unsigned count = 0;
    void operator()(const char*, const char*, int, bool&) override { ++count; }
};

int main()
{
    auto& originalHandler = nvidia::NvGetAssertHandler();
    CountingAssertHandler handler;
    nvidia::NvSetAssertHandler(handler);
    NV_ASSERT(false);
    nvidia::NvSetAssertHandler(originalHandler);
    CHECK(handler.count == NV_ENABLE_ASSERTS);
    NvBlastChunkDesc chunks[2] = {};
    for (unsigned i = 0; i < 2; ++i)
    {
        chunks[i].centroid[0] = static_cast<float>(i);
        chunks[i].volume = 1.0f;
        chunks[i].parentChunkDescIndex = UINT32_MAX;
        chunks[i].flags = NvBlastChunkDesc::SupportFlag;
    }
    NvBlastBondDesc bond = {};
    bond.chunkIndices[1] = 1;
    bond.bond.area = 1.0f;
    bond.bond.normal[0] = 1.0f;
    bond.bond.centroid[0] = 0.5f;
    NvBlastAssetDesc desc = {2, chunks, 1, &bond};
    void* memory = NVBLAST_ALLOC(NvBlastGetAssetMemorySize(&desc, nullptr));
    void* scratch = NVBLAST_ALLOC(NvBlastGetRequiredScratchForCreateAsset(&desc, nullptr));
    CHECK(memory && scratch);
    auto* asset = NvBlastCreateAsset(memory, &desc, scratch, nullptr);
    NVBLAST_FREE(scratch);
    CHECK(asset && NvBlastAssetGetChunkCount(asset, nullptr) == 2);
    NvBlastExtAssetTransformInPlace(asset, nullptr, nullptr, nullptr);
    auto* accelerator = NvBlastExtDamageAcceleratorCreate(asset, 1);
    CHECK(accelerator);
    accelerator->release();

    void* familyMemory = NVBLAST_ALLOC(NvBlastAssetGetFamilyMemorySize(asset, nullptr));
    CHECK(familyMemory);
    auto* family = NvBlastAssetCreateFamily(familyMemory, asset, nullptr);
    CHECK(family);
    NvBlastActorDesc actorDesc = {};
    actorDesc.uniformInitialBondHealth = 1.0f;
    actorDesc.uniformInitialLowerSupportChunkHealth = 1.0f;
    scratch = NVBLAST_ALLOC(NvBlastFamilyGetRequiredScratchForCreateFirstActor(family, nullptr));
    auto* actor = NvBlastFamilyCreateFirstActor(family, &actorDesc, scratch, nullptr);
    NVBLAST_FREE(scratch);
    CHECK(actor);
    auto* stress = Nv::Blast::ExtStressSolver::create(*family);
    CHECK(stress);
    stress->setAllNodesInfoFromLL();
    stress->notifyActorCreated(*actor);
    stress->addForce(0, NvcVec3{100.0f, 0.0f, 0.0f});
    stress->addForce(1, NvcVec3{-100.0f, 0.0f, 0.0f});
    stress->update();
    CHECK(stress->getOverstressedBondCount() == 1);
    stress->release();

    auto* framework = NvBlastTkFrameworkCreate();
    auto* serialization = NvBlastExtSerializationCreate();
    CHECK(framework && serialization);
    CHECK(NvBlastExtTkSerializerLoadSet(*framework, *serialization) > 0);
    CHECK(serialization->setSerializationEncoding(Nv::Blast::ExtSerialization::EncodingID::CapnProtoBinary));
    void* buffer = nullptr;
    const auto size = serialization->serializeIntoBuffer(buffer, asset, Nv::Blast::LlObjectTypeID::Asset);
    CHECK(size > 0);
    uint32_t objectType = 0;
    auto* restored = static_cast<NvBlastAsset*>(serialization->deserializeFromBuffer(buffer, size, &objectType));
    CHECK(restored && objectType == Nv::Blast::LlObjectTypeID::Asset);
    CHECK(NvBlastAssetGetChunkCount(restored, nullptr) == 2);
    NVBLAST_FREE(restored);
    NVBLAST_FREE(buffer);
    serialization->release();
    framework->release();
    NVBLAST_FREE(familyMemory);
    NVBLAST_FREE(memory);
    std::puts("Blast runtime: asset, stress solver, toolkit and serialization passed");
    return 0;
}
