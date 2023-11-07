// Copyright (c) 2023 T4lus Development

#pragma once

#include "MqttClientConfig.generated.h"

USTRUCT(BlueprintType)
struct MQTTUTILITIES_API FMqttClientConfig
{
	GENERATED_BODY()

    /** Host URL. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	FString HostUrl;

	/** Host port. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	int Port;

    /** Unique client identifier. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	FString ClientId;

    /** Maximum time between two pusblish/subscribe tasks executions expressed in miliseconds. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
    int EventLoopDeltaMs{-1};
};