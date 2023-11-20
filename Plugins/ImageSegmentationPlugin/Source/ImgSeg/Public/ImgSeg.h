// Copyright Epic Games, Inc. All Rights Reserved.
// Copyright Plasma Labs, 2023. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Engine/DataTable.h"
#include "Kismet/BlueprintFunctionLibrary.h"


class FToolBarBuilder;
class FMenuBuilder;

class IMGSEG_API FImgSegModule : public IModuleInterface
{
public:

	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	TSharedPtr<class FUICommandList> PluginCommands;
	void RegisterMenus();

	TSharedRef<class SDockTab> OnSpawnPluginTab(const class FSpawnTabArgs& SpawnTabArgs);
	void PluginButtonClicked();

	FReply OnMakePostProcessButtonClick();

	FReply OnTakeCapturesButtonClick();
	FText CurrentText = FText::FromString("Start");
	bool isTakingCaptures = false;

	FString SelectedDirectory;
	void OnDirectoryChanged(const FString& Directory);

	float CaptureDelay = 0.5;
	void CaptureDelayChanged(float value);
	TOptional<float> GetCaptureDelay() const;

	int CaptureNumber = 1;
	void CaptureNumberChanged(int32 value);
	TOptional<int32> GetCaptureNumber() const;
	
};