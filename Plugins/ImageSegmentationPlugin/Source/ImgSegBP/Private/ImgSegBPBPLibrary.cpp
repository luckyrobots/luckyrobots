// Copyright Plasma Labs, 2023. All Rights Reserved.

#include "ImgSegBPBPLibrary.h"
#include "ImgSegBP.h"
#include "SwitchMaterials.h"
#include <Engine/World.h>
#include <Kismet/GameplayStatics.h>
#include "TimerManager.h"
#include "SwitchMaterials.h"
#include <TakeCaptures.h>


UImgSegBPBPLibrary::UImgSegBPBPLibrary(const FObjectInitializer& ObjectInitializer)
: Super(ObjectInitializer)
{

}

bool bIsFlat = false;

void UImgSegBPBPLibrary::ImgSegBPApplyStencilValues()
{
	USwitchMaterials* SwitchMaterials = NewObject<USwitchMaterials>();
	SwitchMaterials->ApplyStencilValues(false);
}

void UImgSegBPBPLibrary::ImgSegBPTakeScreenShot(FString Path, int CaptureIndex)
{	
	UTakeCaptures* TakeCaptures = NewObject<UTakeCaptures>();
	TakeCaptures->TakeCapture(Path, CaptureIndex);
}



