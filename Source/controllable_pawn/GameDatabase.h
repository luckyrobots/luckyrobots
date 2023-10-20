#pragma once

#include "SQLiteDatabase.h"

class GameDatabase
{
public:
    GameDatabase(FString Path, ESQLiteDatabaseOpenMode OpenMode);
    ~GameDatabase();

    bool SaveScreenshot(TArrayView<const uint8> LeftCameraData, TArrayView<const uint8> RightCameraData);

private:
    FSQLiteDatabase* Database;

    FSQLitePreparedStatement SaveStatement;
    FSQLitePreparedStatement LoadStatement;
};