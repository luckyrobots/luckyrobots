// Copyright (c) 2023 T4lus Development

#pragma once

#include "MqttClientBase.h"
#include "Utils/ConversionUtils.h"

#include "MqttClient.generated.h"

UCLASS()
class UMqttClient : public UMqttClientBase
{
	GENERATED_BODY()
	
public:

	void Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback) override;

	void Disconnect(const FOnDisconnectDelegate& onDisconnectCallback) override;

	void Subscribe(FString topic, int qos) override;

	void Unsubscribe(FString topic) override;

	void Publish(FMqttMessage message) override;

public:
	
	void PostInitProperties();
	void BeginDestroy();

	void Init(FMqttClientConfig configData) override;

	void OnConnect();
	void OnDisconnect();
	void OnSubscribe(int messageId, TArray<int> qos);
	void OnUnsubscribe(int messageId);
	void OnPublish(int messageId);
	void OnMessage(FMqttMessage message);
	void OnError(int errCode, FString message);

private:

	TSharedPtr<FJavaClassObject> MqttHelperJavaObject;
	FGuid Guid;
	FJavaClassMethod ConnectMethod;
	FJavaClassMethod DisconnectMethod;
	FJavaClassMethod SubscribeMethod;
	FJavaClassMethod UnsubscribeMethod;
	FJavaClassMethod PublishMethod;
};