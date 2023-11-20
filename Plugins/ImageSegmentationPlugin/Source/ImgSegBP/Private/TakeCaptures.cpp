// Copyright Plasma Labs, 2023. All Rights Reserved.


#include "TakeCaptures.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Misc/Paths.h"

UTakeCaptures::UTakeCaptures()
{
}

void UTakeCaptures::TakeCaptures(int CaptureNumber, float Delay, FString Path)
{
	for (int i = 0; i <= CaptureNumber; i++)
	{
		FTimerHandle TimerHandleCapture;
		FTimerDelegate TimerDel;
		
		FWorldContext* world = GEngine->GetWorldContextFromGameViewport(GEngine->GameViewport);
		UWorld* World = world->World();

		TimerDel.BindUFunction(this, FName("TakeCapture"), Path, i);
		World->GetTimerManager().SetTimer(TimerHandleCapture, TimerDel, Delay * i, false, -1.0f);
		Timers = TimerHandleCapture;
	}
}

void UTakeCaptures::TakeCapture(FString Path, int i)
{
	// find UTextureRenderTarget2D
	UTextureRenderTarget2D* RenderTarget = FindObject<UTextureRenderTarget2D>(ANY_PACKAGE, TEXT("RT_renderTarget_ImgSeg"));
	UTextureRenderTarget2D* RenderTargetSeg = FindObject<UTextureRenderTarget2D>(ANY_PACKAGE, TEXT("RT_renderTarget_ImgSeg_PP"));

	FString filename = FString::FromInt(i) + ".png";

	UKismetRenderingLibrary::ExportRenderTarget(GWorld, RenderTarget, Path + "/images", filename);
	UKismetRenderingLibrary::ExportRenderTarget(GWorld, RenderTargetSeg, Path + "/labels", filename);
}



