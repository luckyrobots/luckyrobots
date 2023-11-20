// Copyright Plasma Labs, 2023. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "ImgSegStyle.h"

class FImgSegCommands : public TCommands<FImgSegCommands>
{
public:

	FImgSegCommands()
		: TCommands<FImgSegCommands>(TEXT("ImgSeg"), NSLOCTEXT("Contexts", "ImgSeg", "ImgSeg Plugin"), NAME_None, FImgSegStyle::GetStyleSetName())
	{
	}

	// TCommands<> interface
	virtual void RegisterCommands() override;

public:
	TSharedPtr< FUICommandInfo > OpenPluginWindow;
};