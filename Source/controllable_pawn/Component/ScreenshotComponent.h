// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraComponent.h"
#include "Components/ActorComponent.h"
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
	void TakeScreenShot(UCameraComponent* LeftCamera, UCameraComponent* RightCamera);
	bool ProcessCamera(UCameraComponent* Camera, TArray<uint8>& OutData);
};
