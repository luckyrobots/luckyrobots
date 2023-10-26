// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraComponent.h"
#include "Components/ActorComponent.h"
#include "Components/SceneCaptureComponent.h"
#include "ScreenshotComponent.generated.h"


UCLASS( ClassGroup=(Custom), meta=(BlueprintSpawnableComponent) )
class CONTROLLABLE_PAWN_API UScreenshotComponent : public UActorComponent
{
	GENERATED_BODY()

public:	
	// Sets default values for this component's properties
	UScreenshotComponent();
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable)
	void DebugScreenshot();
	void OnDebugScreenshotTaken(int32 Width, int32 Height, const TArray<FColor>& Colors);

	UFUNCTION(BlueprintCallable)
	void TakeScreenshot(UCameraComponent* LeftCamera, UCameraComponent* RightCamera);
	bool ProcessCamera(UCameraComponent* Camera, FString TextureName, TArray<uint8>& OutData);

	UFUNCTION(BlueprintCallable)
	void SaveRenderTarget(UTextureRenderTarget2D* LeftRenderTarget, UTextureRenderTarget2D* RightRenderTarget);
	bool ProcessRenderTarget(UTextureRenderTarget2D* RenderTarget, FString TextureName, TArray<uint8>& OutData);

public:

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FVector2D ScreenshotSize;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float TargetGamma;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	ESceneCapturePrimitiveRenderMode PrimitiveRenderMode;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TEnumAsByte<enum ESceneCaptureCompositeMode> CompositeMode;

	UPROPERTY(interp)
	TEnumAsByte<enum ESceneCaptureSource> CaptureSource;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	bool bUseRayTracingIfEnabled;

protected:
	FDelegateHandle RequestScreenshotDelegateHandle;
};
