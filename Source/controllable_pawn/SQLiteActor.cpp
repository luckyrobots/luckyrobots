// Fill out your copyright notice in the Description page of Project Settings.


#include "SQLiteActor.h"

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
	
}

// Called every frame
void ASQLiteActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

void ASQLiteActor::TakeScreenshot() {
	UE_LOG(LogTemp, Log, TEXT("Hello"));
}