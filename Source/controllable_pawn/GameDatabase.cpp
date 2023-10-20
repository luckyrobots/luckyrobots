#include "GameDatabase.h"

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

	const TCHAR* SaveQuery = TEXT("replace into players (id, x, y, z) values ($id, $x, $y, $z)");
	SaveStatement.Create(*Database, SaveQuery, ESQLitePreparedStatementFlags::Persistent);

	const TCHAR* LoadQuery = TEXT("select * from players where id = $id limit 1");
	LoadStatement.Create(*Database, LoadQuery, ESQLitePreparedStatementFlags::Persistent);
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

bool GameDatabase::SavePlayerPosition(int32 PlayerId, FVector Position)
{
	if (Database->IsValid() && SaveStatement.IsValid())
	{
		SaveStatement.Reset();

		bool bBindingSuccess = true;
		bBindingSuccess = bBindingSuccess && SaveStatement.SetBindingValueByName(TEXT("$id"), PlayerId);
		bBindingSuccess = bBindingSuccess && SaveStatement.SetBindingValueByName(TEXT("$x"), Position.X);
		bBindingSuccess = bBindingSuccess && SaveStatement.SetBindingValueByName(TEXT("$y"), Position.Y);
		bBindingSuccess = bBindingSuccess && SaveStatement.SetBindingValueByName(TEXT("$z"), Position.Z);

		if (!bBindingSuccess || !SaveStatement.Execute())
		{
			return false;
		}
	}

	return true;
}

FVector GameDatabase::LoadPlayerPosition(int32 PlayerId)
{
	FVector Position = FVector(0.0f, 0.0f, 0.0f);

	if (Database->IsValid() && LoadStatement.IsValid())
	{
		LoadStatement.Reset();

		if (LoadStatement.SetBindingValueByName(TEXT("$id"), PlayerId) && LoadStatement.Execute() && LoadStatement.Step() == ESQLitePreparedStatementStepResult::Row)
		{
			LoadStatement.GetColumnValueByName(TEXT("x"), Position.X);
			LoadStatement.GetColumnValueByName(TEXT("y"), Position.Y);
			LoadStatement.GetColumnValueByName(TEXT("z"), Position.Z);
		}
	}

	return Position;
}