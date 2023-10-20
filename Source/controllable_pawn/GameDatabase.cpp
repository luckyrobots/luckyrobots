#include "GameDatabase.h"

#include "Misc/DateTime.h"

GameDatabase::GameDatabase(FString Path, ESQLiteDatabaseOpenMode OpenMode)
{
	// OpenMode's:
	// ESQLiteDatabaseOpenMode::ReadOnly (Many connections can read one database)
	// ESQLiteDatabaseOpenMode::ReadWrite (Only one connection can write to database)
	// ESQLiteDatabaseOpenMode::ReadWriteCreate (Only one connection can write and create new tables to database)
	// A connection already opened with ReadWrite/ReadWriteCreate will block other connections with the same OpenMode

	Database = new FSQLiteDatabase();

	if (!Database->Open(*Path, OpenMode) || !Database->IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to open database: %s"), *Database->GetLastError());
	}

	// ? (index)			e.g. select * from people where name = '?'
	// ?integer (index)		e.g. select * from people where name = '?3'
	// :alphanumeric (name) e.g. select * from people where name = ':name'
	// @alphanumeric (name) e.g. select * from people where name = '@name'
	// $alphanumeric (name) e.g. select * from people where name = '@name'

	//const FString SaveQuery = TEXT("INSERT INTO Screenshots (left_camera, right_camera, taken_date) values ($left_camera, $right_camera, $taken_date)");
	//SaveStatement.Create(*Database, *SaveQuery, ESQLitePreparedStatementFlags::Persistent);
}

GameDatabase::~GameDatabase()
{
	SaveStatement.Destroy();
	LoadStatement.Destroy();

	if (!Database->Close())
	{
		UE_LOG(LogTemp, Warning, TEXT("Failed to close database: %s"), *Database->GetLastError());
	}
	else
	{
		delete Database;
	}
}

bool GameDatabase::SaveScreenshot(TArrayView<const uint8> LeftCameraData, TArrayView<const uint8> RightCameraData)
{
	if (Database && Database->IsValid())
	{
		const FString Query = TEXT("INSERT INTO Screenshots (left_camera, right_camera, taken_date) values ($left_camera, $right_camera, $taken_date)");

		FSQLitePreparedStatement Statement;
		Statement.Reset();
		Statement.Create(*Database, *Query, ESQLitePreparedStatementFlags::Persistent);

		bool bBindingSuccess = true;
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