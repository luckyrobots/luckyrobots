// Copyright (c) 2023 T4lus Development

#pragma once

#include "MqttClientBase.h"
#include "CoreMinimal.h"

#include "MqttClient.generated.h"

class FMqttRunnable;
class FRunnableThread;

UCLASS()
class UMqttClient : public UMqttClientBase
{
	GENERATED_BODY()

	friend class FMqttRunnable;

public:

	void BeginDestroy() override;

	void Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback) override;

	void Disconnect(const FOnDisconnectDelegate& onDisconnectCallback) override;

	void Subscribe(FString topic, int qos) override;

	void Unsubscribe(FString topic) override;

	void Publish(FMqttMessage message) override;

public:

	void Init(FMqttClientConfig configData) override;

private:

	FMqttRunnable* Task;
	FRunnableThread* Thread;
	FMqttClientConfig ClientConfig;
};