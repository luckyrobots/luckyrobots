// Copyright (c) 2023 T4lus Development

#include "MqttClientBase.h"

UMqttClientBase::~UMqttClientBase()
{
    
}

void UMqttClientBase::Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback)
{
    // Not implementable
}

void UMqttClientBase::Disconnect(const FOnDisconnectDelegate& onDisconnectCallback)
{
    // Not implementable
}

void UMqttClientBase::Subscribe(FString topic, int qos)
{
    // Not implementable
}

void UMqttClientBase::Unsubscribe(FString topic)
{
    // Not implementable
}

void UMqttClientBase::Publish(FMqttMessage message)
{
    // Not implementable
}

void UMqttClientBase::SetOnPublishHandler(const FOnPublishDelegate& onPublishCallback)
{
    OnPublishDelegate = onPublishCallback;
}

void UMqttClientBase::SetOnMessageHandler(const FOnMessageDelegate& onMessageCallback)
{
    OnMessageDelegate = onMessageCallback;
}

void UMqttClientBase::SetOnSubscribeHandler(const FOnSubscribeDelegate& onSubscribeCallback)
{
    OnSubscribeDelegate = onSubscribeCallback;
}

void UMqttClientBase::SetOnUnsubscribeHandler(const FOnUnsubscribeDelegate& onUnsubscribeCallback)
{
    OnUnsubscribeDelegate = onUnsubscribeCallback;
}

void UMqttClientBase::SetOnErrorHandler(const FOnMqttErrorDelegate& onErrorCallback)
{
	OnErrorDelegate = onErrorCallback;
}

void UMqttClientBase::Init(FMqttClientConfig configData)
{
    // Not implementable. Platform specific MQTT-client initialization
}