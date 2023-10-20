// Fill out your copyright notice in the Description page of Project Settings.


#include "SQLiteActor.h"

#include "GameDatabase.h"


// Sets default values
ASQLiteActor::ASQLiteActor()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

	
}

// Called when the game starts or when spawned
void ASQLiteActor::BeginPlay()
{
	Super::BeginPlay();
	
	FString AbsoluteFilePath = FPaths::ProjectContentDir() + "Database\\db.sqlite";

	Database = new GameDatabase(AbsoluteFilePath, ESQLiteDatabaseOpenMode::ReadWrite);
}

// Called every frame
void ASQLiteActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

void ASQLiteActor::TakeScreenshot() {
	UE_LOG(LogTemp, Log, TEXT("Hello"));


	TArrayView<const uint8> LeftCameraData;
	TArrayView<const uint8> RightCameraData;

	Database->SaveScreenshot(LeftCameraData, RightCameraData);
}