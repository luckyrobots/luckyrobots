// Fill out your copyright notice in the Description page of Project Settings.


#include "DatabaseSubsystem.h"

#include "Misc/DateTime.h"

const FString TruncateScreenShot = "DELETE FROM Screenshots";

const FString Vacuum = "VACUUM";

void UDatabaseSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	Database = new FSQLiteDatabase();

	FString AbsoluteFilePath = FPaths::ProjectContentDir() + "Database\\db.sqlite";

	if (!Database->Open(*AbsoluteFilePath, ESQLiteDatabaseOpenMode::ReadWriteCreate) || !Database->IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to open database: %s"), *Database->GetLastError());
	}

	if (Database->IsValid())
	{
		Database->Execute(*TruncateScreenShot);

		Database->Execute(*Vacuum);
	}

	ScreenshotCount = 0;
	CurrentScreenshot = 0;
}

void UDatabaseSubsystem::Deinitialize()
{
	Super::Deinitialize();

	if (!Database->Close())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to close database: %s"), *Database->GetLastError());
	}
	else
	{
		delete Database;
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
	if (Database && Database->IsValid())
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
		Statement.Create(*Database, *Query, ESQLitePreparedStatementFlags::Persistent);

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
		UE_LOG(LogTemp, Error, TEXT("Database not Valid"));
	}

	return true;
}