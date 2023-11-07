// Copyright (c) 2023 T4lus Development

#include "IMqttUtilitiesModule.h"
#include "Interfaces/IPluginManager.h"
#include "HAL/PlatformProcess.h"

#define LOCTEXT_NAMESPACE "MqttUtilities"

class FMqttUtilitiesModule : public IMqttUtilitiesModule
{
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:

	void* mDllHandleMosquitto;
	void* mDllHandleMosquittopp;
};

IMPLEMENT_MODULE(FMqttUtilitiesModule, MqttUtilities)

void FMqttUtilitiesModule::StartupModule()
{
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module

	// For Windows and Mac platforms dynamic libraries should be loaded manually

#if PLATFORM_WINDOWS

	const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("MqttUtilities"))->GetBaseDir();
	const FString DLLPath = PluginDir / TEXT("Binaries/Win64/");

	FPlatformProcess::PushDllDirectory(*DLLPath);

	mDllHandleMosquitto = FPlatformProcess::GetDllHandle(*(DLLPath + "mosquitto.dll"));
	mDllHandleMosquittopp = FPlatformProcess::GetDllHandle(*(DLLPath + "mosquittopp.dll"));

	FPlatformProcess::PopDllDirectory(*DLLPath);

#endif

#if PLATFORM_MAC

	const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("MqttUtilities"))->GetBaseDir();
	const FString DLLPath = PluginDir / TEXT("Binaries/Mac/");

	FPlatformProcess::PushDllDirectory(*DLLPath);

	mDllHandleMosquitto = FPlatformProcess::GetDllHandle(*(DLLPath + "mosquitto.dylib"));
	mDllHandleMosquittopp = FPlatformProcess::GetDllHandle(*(DLLPath + "mosquittopp.dylib"));

	FPlatformProcess::PopDllDirectory(*DLLPath);

#endif

#if PLATFORM_LINUX

	const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("MqttUtilities"))->GetBaseDir();
	const FString DLLPath = PluginDir / TEXT("Binaries/Linux/");

	FPlatformProcess::PushDllDirectory(*DLLPath);

	mDllHandleMosquitto = FPlatformProcess::GetDllHandle(*(DLLPath + "libmosquitto.so"));
	mDllHandleMosquittopp = FPlatformProcess::GetDllHandle(*(DLLPath + "libmosquittopp.so"));

	FPlatformProcess::PopDllDirectory(*DLLPath);

#endif

}

void FMqttUtilitiesModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.

#if PLATFORM_WINDOWS || PLATFORM_MAC || PLATFORM_LINUX

	if (mDllHandleMosquitto)
	{
		FPlatformProcess::FreeDllHandle(mDllHandleMosquitto);
		mDllHandleMosquitto = nullptr;
	}

	if (mDllHandleMosquittopp)
	{
		FPlatformProcess::FreeDllHandle(mDllHandleMosquittopp);
		mDllHandleMosquittopp = nullptr;
	}

#endif
}

#undef LOCTEXT_NAMESPACE
