// Copyright (c) 2023 T4lus Development

#include "MqttClient.h"
#include "MqttRunnable.h"
#include "MqttTask.h"
#include "Utils/StringUtils.h"
#include "GenericPlatform/GenericPlatformAffinity.h"
#include "HAL/RunnableThread.h"

void UMqttClient::BeginDestroy()
{
	UMqttClientBase::BeginDestroy();

	if (Task != nullptr) 
	{
		Task->StopRunning();
	}
}

void UMqttClient::Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback)
{
	OnConnectDelegate = onConnectCallback;
	
	if (Task != nullptr && Task->IsAlive())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => MQTT task is already running. Disconnect and try again"));
		return;
	}

	if (ClientConfig.ClientId.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => Client ID is not set. Connection cancelled."));
		return;
	}
	
	/** 
	 * All communication between client and broker should be done in a separate thread.
	 * Runnable task stores thread-safe queue for output messages (subscribe, unsubscribe, publish)
	 * and receives broker responsen that are redirected to client.
	*/

	Task = new FMqttRunnable(this);

	Task->Host = std::string(TCHAR_TO_ANSI(*ClientConfig.HostUrl));	
	Task->ClientId = std::string(TCHAR_TO_ANSI(*ClientConfig.ClientId));
	Task->Port = ClientConfig.Port;

	Task->Username = std::string(TCHAR_TO_ANSI(*connectionData.Login));
	Task->Password = std::string(TCHAR_TO_ANSI(*connectionData.Password));

	Thread = FRunnableThread::Create(Task, TEXT("MQTT"), 0, EThreadPriority::TPri_Normal, FGenericPlatformAffinity::GetNoAffinityMask());
}

void UMqttClient::Disconnect(const FOnDisconnectDelegate& onDisconnectCallback)
{
	OnDisconnectDelegate = onDisconnectCallback;
	
	if (Task != nullptr) 
	{
		Task->StopRunning();
	}

	Task = nullptr;
}

void UMqttClient::Subscribe(FString topic, int qos)
{
	if(Task == nullptr || !Task->IsAlive())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => There is no running MQTT task"));
		return;
	}

	char* sub = StringUtils::CopyString(topic);
	
	FMqttSubscribeTaskPtr taskSubscribe = MakeShared<FMqttSubscribeTask>();;
	taskSubscribe->type = MqttTaskType::Subscribe;
	taskSubscribe->qos = qos;
	taskSubscribe->sub = sub;

	Task->PushTask(taskSubscribe);
}

void UMqttClient::Unsubscribe(FString topic)
{
	if(Task == nullptr || !Task->IsAlive())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => There is no running MQTT task"));
		return;
	}

	char* sub = StringUtils::CopyString(topic);

	FMqttUnsubscribeTaskPtr taskUnsubscribe = MakeShared<FMqttUnsubscribeTask>();
	taskUnsubscribe->type = MqttTaskType::Unsubscribe;
	taskUnsubscribe->sub = sub;
	
	Task->PushTask(taskUnsubscribe);
}

void UMqttClient::Publish(FMqttMessage message)
{
	if(Task == nullptr || !Task->IsAlive())
	{
		UE_LOG(LogTemp, Warning, TEXT("MQTT => There is no running MQTT task"));
		return;
	}

	char* sub = StringUtils::CopyString(message.Topic);
	char* msg = StringUtils::CopyString(message.Message);

	FMqttPublishTaskPtr taskPublish = MakeShared<FMqttPublishTask>();
	taskPublish->type = MqttTaskType::Publish;
	taskPublish->topic = sub;
	taskPublish->payloadlen = (int)strlen(msg);
	taskPublish->payload = msg;
	taskPublish->qos = message.Qos;
	taskPublish->retain = message.Retain;	

	Task->PushTask(taskPublish);
}

void UMqttClient::Init(FMqttClientConfig configData)
{
	ClientConfig = configData;
}