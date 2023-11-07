// Copyright (c) 2023 T4lus Development

#include "MqttClientHolder.h"
#include "Async/Async.h"

#if PLATFORM_ANDROID
#include "Android/AndroidApplication.h"
#include "Android/AndroidJNI.h"
#endif

static MqttClientHolder* pHolder = nullptr;

MqttClientHolder::MqttClientHolder()
{

}

MqttClientHolder * MqttClientHolder::GetInstance()
{
	if (!pHolder)
	{
		pHolder = new MqttClientHolder();
	}

	return pHolder;
}

void MqttClientHolder::AddClient(FGuid guid, UMqttClient * client)
{
	Clients.Add(guid, client);
}

void MqttClientHolder::RemoveClient(FGuid guid)
{
	Clients.Remove(guid);
}

UMqttClient * MqttClientHolder::GetClient(FGuid guid) const
{
	if (Clients.Find(guid))
	{
		return Clients[guid];
	}

	return nullptr;
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onConnected(JNIEnv* env, jclass clazz, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onConnected"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnConnect();
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onDisconnected(JNIEnv* env, jclass clazz, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onDisconnected"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnDisconnect();
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onSubscribed(JNIEnv* env, jclass clazz, int messageId, jintArray qos, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onSubscribed"));
	TArray<int> qosArray = ConversionUtils::ConvertToIntArray(qos);

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnSubscribe(messageId, qosArray);
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onUnsubscribed(JNIEnv* env, jclass clazz, int messageId, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onUnsubscribed"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnUnsubscribe(messageId);
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onPublished(JNIEnv* env, jclass clazz, int messageId, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onPublished"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnPublish(messageId);
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onMessageArrived(JNIEnv* env, jclass clazz, jstring topic, jobject javaMessage, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onMessageArrived"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;
	FMqttMessage message = ConversionUtils::ConvertFromJavaMessage(topic, javaMessage);

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnMessage(message);
			});
		}		
	}
}

JNI_METHOD void Java_com_ninevastudios_mqttdemo_MqttHelper_onError(JNIEnv* env, jclass clazz, int errCode, jstring errMessage, jstring guid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTTCLIENT => Java_com_ninevastudios_mqttdemo_MqttHelper_onError"));

	FString strGuid = ConversionUtils::FromJavaString(guid);

	if (!pHolder)
	{
		return;
	}

	FGuid clientGuid;

	FString errorMessage = ConversionUtils::FromJavaString(errMessage);

	if (FGuid::Parse(strGuid, clientGuid))
	{
		auto client = pHolder->GetClient(clientGuid);
		if (client)
		{
			AsyncTask(ENamedThreads::GameThread, [=]() {
				client->OnError(errCode, errorMessage);
			});
		}
	}
}