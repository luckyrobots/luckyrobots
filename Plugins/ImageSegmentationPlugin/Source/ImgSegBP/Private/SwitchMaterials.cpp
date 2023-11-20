// Copyright Plasma Labs, 2023. All Rights Reserved.

#include "SwitchMaterials.h"
#include "ImgSegBPBPLibrary.h"
#include <Kismet/GameplayStatics.h>
#include "Engine/StaticMeshActor.h"
#include "Components/MeshComponent.h"
#include "ImgSegBP.h"
#include "TimerManager.h"
#include "LandscapeStreamingProxy.h"
#include "Misc/FileHelper.h"


// Sets default values
USwitchMaterials::USwitchMaterials()
{
}

void USwitchMaterials::ApplyStencilValues(bool bCsvOnly)
{
	TArray<AActor*> FoundActors;
	TSet<UActorComponent*> FoundComponents;
	int StencilValue = 1;

	// load swicth materials class
	USwitchMaterials* SwitchMaterials = NewObject<USwitchMaterials>();
	FoundActors = SwitchMaterials->FindActors("seg");

	for (int i = 0; i < FoundActors.Num(); i++) {

		TArray<UMeshComponent*> Components;
		FoundActors[i]->GetComponents<UMeshComponent>(Components);


		for (int32 j = 0; j < Components.Num(); j++)
		{
			UMeshComponent* MeshComponent = Components[j];

			//get actor tag
			FString ActorTag = FoundActors[i]->Tags[0].ToString();

			// check if ActorTag is already in dictionary
			if (MeshDataMap.Contains(ActorTag)) {
			}
			else {
				// add path to dictionary
				MeshDataMap.Add(ActorTag, StencilValue++);
			}

			if (!bCsvOnly) {
				// set custom depth stencil value
				MeshComponent->SetRenderCustomDepth(true);
				MeshComponent->SetCustomDepthStencilValue(MeshDataMap[ActorTag]);
			}
			
		}
	}
}

TArray<AActor*> USwitchMaterials::FindActors(FName Tag)
{

	TArray<AActor*> FoundActors;
	//UWorld* World = GetWorld();
	FWorldContext* world = GEngine->GetWorldContextFromGameViewport(GEngine->GameViewport);
	UWorld* World = world->World();
	if (World) {
		//UGameplayStatics::GetAllActorsOfClass(World, ActorCLass, FoundActors);
		UGameplayStatics::GetAllActorsWithTag(World, Tag, FoundActors);
		if (FoundActors.Num() > 0) {
			return FoundActors;
		}

	}
	// LOG AN ERROR HERE
	return FoundActors;
}


void USwitchMaterials::WriteMapToFile(FString Path)
{	
	// write csv
	FString FilePath = Path + "/labels.csv";
	// log path
	FString String = "empty,0\n";
	for (auto& Elem : MeshDataMap)
	{
		String += Elem.Key + "," + FString::FromInt(Elem.Value) + "\n";
	}
	FFileHelper::SaveStringToFile(String, *FilePath);
}
