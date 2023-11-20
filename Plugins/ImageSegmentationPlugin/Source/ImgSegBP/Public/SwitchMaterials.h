// Copyright Plasma Labs, 2023. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Engine/DataTable.h"
#include "SwitchMaterials.generated.h"


UCLASS()
class IMGSEGBP_API USwitchMaterials : public UObject

{
	GENERATED_BODY()

public:
	USwitchMaterials();

	UFUNCTION(BlueprintCallable, Category = "ImgSegBP")
	void ApplyStencilValues(bool bCsvOnly);
	TArray<AActor*> FindActors(FName Tag);
	TMap<FString, INT> MeshDataMap;
	void WriteMapToFile(FString Path);

};

