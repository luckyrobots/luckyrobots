// Fill out your copyright notice in the Description page of Project Settings.


#include "DatabaseSubsystem.h"

#include "Misc/DateTime.h"

const FString TruncateScreenShot = "DELETE FROM Screenshots";
const FString TruncateMovements = "DELETE FROM Movements";

const FString Vacuum = "VACUUM";

void UDatabaseSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	OutputDatabase = new FSQLiteDatabase();
	InputDatabase = new FSQLiteDatabase();

	FString OutputAbsoluteFilePath = FPaths::ProjectContentDir() + "Database\\output.sqlite";
	FString InputAbsoluteFilePath = FPaths::ProjectContentDir() + "Database\\input.sqlite";

	if (!OutputDatabase->Open(*OutputAbsoluteFilePath, ESQLiteDatabaseOpenMode::ReadWriteCreate) || !OutputDatabase->IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to open Output database: %s"), *OutputDatabase->GetLastError());
	}

	if (!InputDatabase->Open(*InputAbsoluteFilePath, ESQLiteDatabaseOpenMode::ReadOnly) || !InputDatabase->IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to open Input database: %s"), *InputDatabase->GetLastError());
	}

	if (OutputDatabase->IsValid())
	{
		OutputDatabase->Execute(*TruncateScreenShot);

		OutputDatabase->Execute(*Vacuum);
	}

	if (InputDatabase->IsValid())
	{
		InputDatabase->Execute(*TruncateMovements);

		InputDatabase->Execute(*Vacuum);
	}

	ScreenshotCount = 0;
	CurrentScreenshot = 0;
}

void UDatabaseSubsystem::Deinitialize()
{
	Super::Deinitialize();

	if (!OutputDatabase->Close())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to close database: %s"), *OutputDatabase->GetLastError());
	}
	else
	{
		delete OutputDatabase;
	}
}

bool UDatabaseSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	TArray<UClass*> ChildClasses;
	GetDerivedClasses(GetClass(), ChildClasses, false);

	// Only create an instance if there is not a game-specific subclass
	return ChildClasses.Num() == 0;
}

bool UDatabaseSubsystem::SaveScreenshot(TArrayView<const uint8> LeftCameraData, TArrayView<const uint8> RightCameraData)
{
	if (OutputDatabase && OutputDatabase->IsValid())
	{
		FString Query;

		if (ScreenshotCount < 60)
		{
			ScreenshotCount++;
			CurrentScreenshot++;
			Query = TEXT("INSERT INTO Screenshots (id, left_camera, right_camera, taken_date) values ($id, $left_camera, $right_camera, $taken_date)");
		}
		else
		{
			CurrentScreenshot++;

			if (CurrentScreenshot >= 60)
			{
				CurrentScreenshot = 1;
			}
			Query = TEXT("UPDATE Screenshots SET left_camera = $left_camera, right_camera = $right_camera, taken_date = $taken_date WHERE id = $id");
		}

		FSQLitePreparedStatement Statement;
		Statement.Reset();
		Statement.Create(*OutputDatabase, *Query, ESQLitePreparedStatementFlags::Persistent);

		bool bBindingSuccess = true;
		bBindingSuccess = bBindingSuccess && Statement.SetBindingValueByName(TEXT("$id"), CurrentScreenshot);
		bBindingSuccess = bBindingSuccess && Statement.SetBindingValueByName(TEXT("$left_camera"), LeftCameraData);
		bBindingSuccess = bBindingSuccess && Statement.SetBindingValueByName(TEXT("$right_camera"), RightCameraData);
		bBindingSuccess = bBindingSuccess && Statement.SetBindingValueByName(TEXT("$taken_date"), FDateTime::Now().ToUnixTimestamp());

		if (!bBindingSuccess || !Statement.Execute())
		{
			return false;
		}
	}
	else {
		UE_LOG(LogTemp, Error, TEXT("OutputDatabase not Valid"));
	}

	return true;
}

FDatabaseMovements UDatabaseSubsystem::GetLastMovement()
{
	if (InputDatabase && InputDatabase->IsValid())
	{
		FString Query = TEXT("SELECT command, scale FROM Movements ORDER BY created_at DESC LIMIT 1");
		

		FSQLitePreparedStatement Statement;
		Statement.Reset();
		Statement.Create(*InputDatabase, *Query, ESQLitePreparedStatementFlags::Persistent);

		FDatabaseMovements Result;

		while (Statement.Step() == ESQLitePreparedStatementStepResult::Row)
		{
			Statement.GetColumnValueByName(TEXT("command"), Result.Command);
			Statement.GetColumnValueByName(TEXT("scale"), Result.Scale);
		}

		return Result;
		
	}
	else {
		UE_LOG(LogTemp, Error, TEXT("InputDatabase not Valid"));
	}

	return FDatabaseMovements();
}