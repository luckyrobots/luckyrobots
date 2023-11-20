// Copyright Plasma Labs, 2023. All Rights Reserved.

#include "ImgSegBP.h"

#define LOCTEXT_NAMESPACE "FImgSegBPModule"

void FImgSegBPModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module
	
}

void FImgSegBPModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
	
}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FImgSegBPModule, ImgSegBP)