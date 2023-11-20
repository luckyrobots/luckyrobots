// Copyright Plasma Labs, 2023. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Engine/DataTable.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "ImgSegBP.generated.h"


class FImgSegBPModule : public IModuleInterface
{
public:

	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;
};

USTRUCT(BlueprintType)
struct FMeshData : public FTableRowBase
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString ActorName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString ActorTag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString MeshName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString MaterialPath;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString FlatMaterialPath;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		FString MaterialName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		int32 MeshID;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		int32 MaterialID;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MeshData")
		int32 index;
};