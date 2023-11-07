// Copyright (c) 2023 T4lus Development

#include "MqttTask.h"

FMqttSubscribeTask::FMqttSubscribeTask() : FMqttTask()
	,qos(0)
	,sub(nullptr) 
{
}

FMqttSubscribeTask::~FMqttSubscribeTask()
{
}

FMqttUnsubscribeTask::FMqttUnsubscribeTask() : FMqttTask()
	,sub(nullptr) 
{
}

FMqttUnsubscribeTask::~FMqttUnsubscribeTask()
{
	if(sub != nullptr)
	{
		free(sub);
		sub = nullptr;
	}
}

FMqttPublishTask::FMqttPublishTask() : FMqttTask()
	, topic(nullptr)
	, payloadlen(0)
	, payload(nullptr)
	, qos(0)
	, retain(false) 
{
}

FMqttPublishTask::~FMqttPublishTask()
{
	if(topic != nullptr)
	{
		free(topic);
		topic = nullptr;
	}

	if(payload != nullptr)
	{
		free(payload);
		payload = nullptr;
	}
}