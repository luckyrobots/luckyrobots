// Copyright (c) 2023 T4lus Development

#pragma once

#include "MqttMessage.generated.h"

USTRUCT(BlueprintType)
struct MQTTUTILITIES_API FMqttMessage
{
	GENERATED_BODY()

	/** Message topic. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	FString Topic;

	/** Message content. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	FString Message;

	/** Message content buffer. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	TArray<uint8> MessageBuffer;

	/** Retain flag. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	bool Retain;

	/** Quality of signal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MQTT")
	int Qos;
};