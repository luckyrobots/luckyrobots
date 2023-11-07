// Copyright (c) 2023 T4lus Development

#include "MqttRunnable.h"

#include "MqttClient.h"
#include "MqttClientImpl.h"

#include "Async/Async.h"

FMqttRunnable::FMqttRunnable(UMqttClient* mqttClient, int updateDeltaMs) : FRunnable()
	,iUpdateDeltaMs(updateDeltaMs)
	,TaskQueue(new std::queue<FMqttTaskPtr>())
	,TaskQueueLock(new FCriticalSection())
	,client(mqttClient)
{
}

FMqttRunnable::~FMqttRunnable()
{	
	if (TaskQueueLock != nullptr)
	{
		delete TaskQueueLock;
		TaskQueueLock = nullptr;
	}
	
	if (TaskQueue != nullptr)
	{
		delete TaskQueue;
		TaskQueue = nullptr;
	}
}

bool FMqttRunnable::Init()
{
	bKeepRunning = true;
	return true;
}

void FMqttRunnable::Stop()
{
	StopRunning();
}

uint32 FMqttRunnable::Run()
{
	mosqpp::lib_init();

	MqttClientImpl connection(ClientId.c_str());
	
	connection.max_inflight_messages_set(0);
	connection.Task = this;

	int returnCode = 0;
	
	if (!Username.empty()) 
	{
		connection.username_pw_set(Username.c_str(), Password.c_str());
	}
	
	returnCode = connection.connect(Host.c_str(), Port, 10);

	if (returnCode != 0) 
	{
		UE_LOG(LogTemp, Error, TEXT("MQTT => Connection error: %s"), ANSI_TO_TCHAR(mosquitto_strerror(returnCode)));
		OnError(returnCode, FString(ANSI_TO_TCHAR(mosquitto_strerror(returnCode))));
		bKeepRunning = false;
	}

	while (bKeepRunning) 
	{
		TaskQueueLock->Lock();

		while (TaskQueue != nullptr)
		{
			if (TaskQueue->empty())
			{
				break;
			}
			
			FMqttTaskPtr task = TaskQueue->front();
			TaskQueue->pop();

			switch (task->type) 
			{
				case MqttTaskType::Subscribe: {
					auto taskSubscribe = StaticCastSharedPtr<FMqttSubscribeTask>(task);
					returnCode = connection.subscribe(NULL, taskSubscribe->sub, taskSubscribe->qos);
					break;
				}
				case MqttTaskType::Unsubscribe: {
					auto taskUnsubscribe = StaticCastSharedPtr<FMqttUnsubscribeTask>(task);
					returnCode = connection.unsubscribe(NULL, taskUnsubscribe->sub);
					break;
				}
				case MqttTaskType::Publish:	{
					auto taskPublish = StaticCastSharedPtr<FMqttPublishTask>(task);
					returnCode = connection.publish(NULL, taskPublish->topic, taskPublish->payloadlen, taskPublish->payload, taskPublish->qos, taskPublish->retain);
					break;
				}
			}

			if (returnCode != 0)
			{
				UE_LOG(LogTemp, Error, TEXT("MQTT => Output error: %s"), ANSI_TO_TCHAR(mosquitto_strerror(returnCode)));
				OnError(returnCode, FString(ANSI_TO_TCHAR(mosquitto_strerror(returnCode))));
			}
		}

		TaskQueueLock->Unlock();

		returnCode = connection.loop(iUpdateDeltaMs);

		if (returnCode != 0)
		{
			UE_LOG(LogTemp, Error, TEXT("MQTT => Connection error: %s"), ANSI_TO_TCHAR(mosquitto_strerror(returnCode)));

			if(returnCode == MOSQ_ERR_CONN_REFUSED)
			{
				OnError(returnCode, FString(ANSI_TO_TCHAR(mosquitto_strerror(returnCode))));
				bKeepRunning = false;
			}
			else
			{
				connection.reconnect();
			}			
		}
	}

	returnCode = connection.disconnect();
	
	if (returnCode != 0) 
	{
		UE_LOG(LogTemp, Error, TEXT("MQTT => %s"), ANSI_TO_TCHAR(mosquitto_strerror(returnCode)));
	}

	delete TaskQueue;
	delete TaskQueueLock;
	
	TaskQueue = nullptr;
	TaskQueueLock = nullptr;

	return 0;
}

void FMqttRunnable::StopRunning()
{
	bKeepRunning = false;
}

bool FMqttRunnable::IsAlive() const
{
	return bKeepRunning;
}

void FMqttRunnable::PushTask(FMqttTaskPtr task)
{
	TaskQueueLock->Lock();
	
	if (TaskQueue != nullptr)
	{
		TaskQueue->push(task);
	}
	
	TaskQueueLock->Unlock();
}

void FMqttRunnable::OnConnect()
{
	AsyncTask(ENamedThreads::GameThread, [this]() {
		client->OnConnectDelegate.ExecuteIfBound();
	});
}

void FMqttRunnable::OnDisconnect()
{
	AsyncTask(ENamedThreads::GameThread, [this]() {
		client->OnDisconnectDelegate.ExecuteIfBound();
	});
}

void FMqttRunnable::OnPublished(int mid)
{
	AsyncTask(ENamedThreads::GameThread, [this, mid]() {
		client->OnPublishDelegate.ExecuteIfBound(mid);
	});
}

void FMqttRunnable::OnMessage(FMqttMessage message)
{
	AsyncTask(ENamedThreads::GameThread, [this, message]() {
		client->OnMessageDelegate.ExecuteIfBound(message);
	});
}

void FMqttRunnable::OnSubscribe(int mid, const TArray<int> qos)
{
	AsyncTask(ENamedThreads::GameThread, [this, mid, qos]() {
		client->OnSubscribeDelegate.ExecuteIfBound(mid, qos);
		});
}


void FMqttRunnable::OnUnsubscribe(int mid)
{
	AsyncTask(ENamedThreads::GameThread, [this, mid]() {
		client->OnUnsubscribeDelegate.ExecuteIfBound(mid);
		});
}


void FMqttRunnable::OnError(int errCode, FString message)
{
	AsyncTask(ENamedThreads::GameThread, [this, errCode, message]() {
		client->OnErrorDelegate.ExecuteIfBound(errCode, message);
		});
}

