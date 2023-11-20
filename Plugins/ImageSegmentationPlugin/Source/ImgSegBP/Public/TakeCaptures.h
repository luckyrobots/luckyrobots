// Copyright Plasma Labs, 2023. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "TakeCaptures.generated.h"


UCLASS()
class IMGSEGBP_API UTakeCaptures : public UObject
{
	GENERATED_BODY()

		public:
			UTakeCaptures();

			FString CapturePath;
			int CaptureI;
			FTimerHandle Timers;
			UFUNCTION(BlueprintCallable, Category = "ImgSegBP")
			void TakeCapture(FString Path, int i);
			void TakeCaptures(int CaptureNumber, float Delay, FString Path);

		



			
	
};
