// Copyright (c) 2023 T4lus Development

#pragma once

#include "Modules/ModuleManager.h"

class IMqttUtilitiesModule : public IModuleInterface
{
public:

	static inline IMqttUtilitiesModule& Get()
	{
		return FModuleManager::LoadModuleChecked<IMqttUtilitiesModule>("MqttUtilities");
	}

	static inline bool IsAvailable()
	{
		return FModuleManager::Get().IsModuleLoaded("MqttUtilities");
	}
};
