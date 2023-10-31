// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "SQLiteDatabase.h"
#include "Subsystems/GameInstanceSubsystem.h"

#include "DatabaseSubsystem.generated.h"


USTRUCT(BlueprintType)
struct FDatabaseMovements
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FString Command;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float Scale;

	FDatabaseMovements(FString _Command = "", float _Scale = 0.f)
	{
		Command = _Command;
		Scale = _Scale;
	}
};

UCLASS()
class CONTROLLABLE_PAWN_API UDatabaseSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	UDatabaseSubsystem() { }

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;

	bool SaveScreenshot(TArrayView<const uint8> LeftCameraData, TArrayView<const uint8> RightCameraData);

	UFUNCTION(BlueprintCallable)
	FDatabaseMovements GetLastMovement();

private:
	FSQLiteDatabase* OutputDatabase;
	FSQLiteDatabase* InputDatabase;

private:
	int32 ScreenshotCount;
	int32 CurrentScreenshot;

};
