// Copyright Plasma Labs, 2023. All Rights Reserved.

#include "ImgSegCommands.h"

#define LOCTEXT_NAMESPACE "FImgSegModule"

void FImgSegCommands::RegisterCommands()
{
	UI_COMMAND(OpenPluginWindow, "Image Segmentation", "Image Segmentation", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
