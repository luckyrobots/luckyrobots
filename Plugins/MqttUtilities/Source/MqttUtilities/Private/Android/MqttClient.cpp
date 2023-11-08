// Copyright (c) 2023 T4lus Development

#include "MqttClient.h"
#include "MqttClientHolder.h"

void UMqttClient::PostInitProperties()
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => UMqttClient::PostInitProperties()"));

	Super::PostInitProperties();

	if (UMqttClient::StaticClass()->GetDefaultObject() != this)
	{
		// add to root to avoid GC issues
		AddToRoot();
	}
}

void UMqttClient::BeginDestroy()
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => UMqttClient::BeginDestroy()"));

	if (UMqttClient::StaticClass()->GetDefaultObject() != this)
	{
		MqttClientHolder::GetInstance()->RemoveClient(Guid);

		// remove from root so now it can be safely destroyed by GC
		RemoveFromRoot();
	}

	Super::BeginDestroy();
}

void UMqttClient::Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback)
{
	OnConnectDelegate = onConnectCallback;
	
	FJavaClassObject* javaConnectionData = ConversionUtils::ConvertToJavaConnectionData(connectionData);

	MqttHelperJavaObject->CallMethod<void>(ConnectMethod, javaConnectionData->GetJObject());
}

void UMqttClient::Disconnect(const FOnDisconnectDelegate& onDisconnectCallback)
{
	OnDisconnectDelegate = onDisconnectCallback;
	
	MqttHelperJavaObject->CallMethod<void>(DisconnectMethod, 0);
}

void UMqttClient::Subscribe(FString topic, int qos)
{
	if (topic.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => Topic is not set. Subscription cancelled."));
		return;
	}
	
	MqttHelperJavaObject->CallMethod<void>(SubscribeMethod, ConversionUtils::GetJavaString(topic), qos);
}

void UMqttClient::Unsubscribe(FString topic)
{
	if (topic.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => Topic is not set. Unsubscription cancelled."));
		return;
	}
	
	MqttHelperJavaObject->CallMethod<void>(UnsubscribeMethod, ConversionUtils::GetJavaString(topic));
}

void UMqttClient::Publish(FMqttMessage message)
{
	FJavaClassObject* javaMessage = ConversionUtils::ConvertToJavaMessage(message);
	MqttHelperJavaObject->CallMethod<void>(PublishMethod, javaMessage->GetJObject(), ConversionUtils::GetJavaString(message.Topic));
}

void UMqttClient::Init(FMqttClientConfig configData)
{
	FString url = FString::Printf(TEXT("tcp://%s:%d"), *configData.HostUrl, configData.Port);
	Guid = FGuid::NewGuid();
	MqttClientHolder::GetInstance()->AddClient(Guid, this);

	MqttHelperJavaObject = MakeShareable(new FJavaClassObject("com/ninevastudios/mqttdemo/MqttHelper", 
		"(Landroid/app/Activity;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V", FJavaWrapper::GameActivityThis, 
		ConversionUtils::GetJavaString(url), ConversionUtils::GetJavaString(configData.ClientId), ConversionUtils::GetJavaString(Guid.ToString())));

	ConnectMethod = MqttHelperJavaObject->GetClassMethod("connect", "(Lorg/eclipse/paho/client/mqttv3/MqttConnectOptions;)V");
	DisconnectMethod = MqttHelperJavaObject->GetClassMethod("disconnect", "(I)V");
	SubscribeMethod = MqttHelperJavaObject->GetClassMethod("subscribeToTopic", "(Ljava/lang/String;I)V");
	UnsubscribeMethod = MqttHelperJavaObject->GetClassMethod("unsubscribeFromTopic", "(Ljava/lang/String;)V");
	PublishMethod = MqttHelperJavaObject->GetClassMethod("publishMessage", "(Lorg/eclipse/paho/client/mqttv3/MqttMessage;Ljava/lang/String;)V");
}

void UMqttClient::OnConnect()
{
	OnConnectDelegate.ExecuteIfBound();
}

void UMqttClient::OnDisconnect()
{
	OnDisconnectDelegate.ExecuteIfBound();
}

void UMqttClient::OnSubscribe(int messageId, TArray<int> qos)
{
	OnSubscribeDelegate.ExecuteIfBound(messageId, qos);
}

void UMqttClient::OnUnsubscribe(int messageId)
{
	OnUnsubscribeDelegate.ExecuteIfBound(messageId);
}

void UMqttClient::OnPublish(int messageId)
{
	OnPublishDelegate.ExecuteIfBound(messageId);
}

void UMqttClient::OnMessage(FMqttMessage message)
{
	OnMessageDelegate.ExecuteIfBound(message);
}

void UMqttClient::OnError(int errCode, FString message)
{
	OnErrorDelegate.ExecuteIfBound(errCode, message);
}
