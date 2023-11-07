// Copyright (c) 2023 T4lus Development

#pragma once

#include "Interface/MqttClientInterface.h"
#include "Entities/MqttClientConfig.h"

#include "Kismet/BlueprintFunctionLibrary.h"

#include "MqttUtilitiesBPL.generated.h"

UCLASS()
class MQTTUTILITIES_API UMqttUtilitiesBPL : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

	/**
	 * Create new instance of MQTT client
	 *
	 * @return - reference to MQTT client interface object
	 */
public:
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	static TScriptInterface<IMqttClientInterface> CreateMqttClient(FMqttClientConfig config);
};