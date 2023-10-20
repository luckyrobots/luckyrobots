#pragma once

#include "SQLiteDatabase.h"

class GameDatabase
{
public:
    GameDatabase(FString Path, ESQLiteDatabaseOpenMode OpenMode);
    ~GameDatabase();

    bool SavePlayerPosition(int32 PlayerId, FVector Position);
    FVector LoadPlayerPosition(int32 PlayerId);

private:
    FSQLiteDatabase* Database;

    FSQLitePreparedStatement SaveStatement;
    FSQLitePreparedStatement LoadStatement;
};