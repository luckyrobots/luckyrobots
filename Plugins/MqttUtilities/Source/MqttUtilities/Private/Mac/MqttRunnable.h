// Copyright (c) 2023 T4lus Development

#pragma once

#include "CoreMinimal.h"
#include "HAL/Runnable.h"

#include "Entities/MqttMessage.h"
#include "MqttTask.h"

#include <queue>
#include <string>

class UMqttClient;

class FMqttRunnable : public FRunnable
{
public:

	FMqttRunnable(UMqttClient* mqttClient, int updateDeltaMs = -1);
	virtual ~FMqttRunnable();
	
	bool Init() override;
	uint32 Run() override;
	void Stop() override;

	void PushTask(FMqttTaskPtr task);

	void StopRunning();

	bool IsAlive() const;

private:
	
	bool bKeepRunning;

	int iUpdateDeltaMs;

	std::queue<FMqttTaskPtr>* TaskQueue;

	FCriticalSection* TaskQueueLock;

	UMqttClient* client;

public:

	std::string Host;
	std::string ClientId;
	std::string Username;
	std::string Password;
	
	int32 Port;

	void OnConnect();
	void OnDisconnect();
	void OnPublished(int mid);
	void OnMessage(FMqttMessage message);
	void OnSubscribe(int mid, const TArray<int> qos);
	void OnUnsubscribe(int mid);
	void OnError(int errCode, FString message);
};