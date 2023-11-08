// Copyright (c) 2023 T4lus Development

#pragma once

#include "UObject/Interface.h"

#include "Entities/MqttMessage.h"
#include "Entities/MqttConnectionData.h"
#include "Entities/MqttClientConfig.h"

#include "MqttClientInterface.generated.h"

DECLARE_DYNAMIC_DELEGATE(FOnConnectDelegate);
DECLARE_DYNAMIC_DELEGATE(FOnDisconnectDelegate);
DECLARE_DYNAMIC_DELEGATE_OneParam(FOnPublishDelegate, int, mid);
DECLARE_DYNAMIC_DELEGATE_OneParam(FOnMessageDelegate, FMqttMessage, message);
DECLARE_DYNAMIC_DELEGATE_TwoParams(FOnSubscribeDelegate, int, mid, const TArray<int>&, qos);
DECLARE_DYNAMIC_DELEGATE_OneParam(FOnUnsubscribeDelegate, int, mid);
DECLARE_DYNAMIC_DELEGATE_TwoParams(FOnMqttErrorDelegate, int, code, FString, message);

UINTERFACE(BlueprintType, meta = (CannotImplementInterfaceInBlueprint))
class MQTTUTILITIES_API UMqttClientInterface : public UInterface
{
	GENERATED_BODY()
};

class MQTTUTILITIES_API IMqttClientInterface
{
	GENERATED_BODY()

public:

	/**
	 * Connect to MQTT broker
	 * @param connectionData - structure with data required to connect to MQTT broker (host url, port, client id etc.)
	 * @param onConnectCallback - callback function handler triigered after client successfully established connection with MQTT broker 
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback) = 0;

	/**
	 * Disconnect from MQTT broker
	 * @param onDisconnectCallback - callback function handler triigered after client was disconnected from MQTT broker
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void Disconnect(const FOnDisconnectDelegate& onDisconnectCallback) = 0;

	/**
	 * Subscribe to topic
	 * @param topic - name of the topic
	 * @param qos - level of quality of service
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void Subscribe(FString topic, int qos) = 0;

	/**
	 * Unsubscribe from topic
	 * @param topic - name of the topic
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void Unsubscribe(FString topic) = 0;

	/**
	 * Publish message
	 * @param message - structure with message data (topic, QoS, payload etc.)
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void Publish(FMqttMessage message) = 0;

	/**
	 * Set handler for message publishing event
	 * @param onPublishCallback - callback function handler triigered after client message was published to MQTT broker
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void SetOnPublishHandler(const FOnPublishDelegate& onPublishCallback) = 0;

	/**
	 * Set handler for message receiving event
	 * @param onMessageCallback - callback function handler triigered after client received message from MQTT broker
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void SetOnMessageHandler(const FOnMessageDelegate& onMessageCallback) = 0;

	/**
	 * Set handler for subscription event
	 * @param onSubscribeCallback - callback function handler triigered after client subscribed to topic exposed by MQTT broker
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void SetOnSubscribeHandler(const FOnSubscribeDelegate& onSubscribeCallback) = 0;

	/**
	 * Set handler for unsubscription event
	 * @param onUnsubscribeCallback - callback function handler triigered after client unsubscribed from topic exposed by MQTT broker
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void SetOnUnsubscribeHandler(const FOnUnsubscribeDelegate& onUnsubscribeCallback) = 0;

	/**
	 * Set handler for error event
	 * @param onErrorCallback - callback function handler triigered after any MQTT-related error occured
	 */
	UFUNCTION(BlueprintCallable, Category = "MQTT")
	virtual void SetOnErrorHandler(const FOnMqttErrorDelegate& onErrorCallback) = 0;
};

typedef TSharedPtr<class IMqttClientInterface, ESPMode::ThreadSafe> IMqttClientPtr;