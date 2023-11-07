// Copyright (c) 2023 T4lus Development

#pragma once

enum class MqttTaskType
{
	Publish,
	Subscribe,
	Unsubscribe,
};

struct FMqttTask
{	
	MqttTaskType type;
};

struct FMqttSubscribeTask : public FMqttTask
{
	FMqttSubscribeTask();
	virtual ~FMqttSubscribeTask();
	
	int qos;
	char* sub;
};

struct FMqttUnsubscribeTask : public FMqttTask
{
	FMqttUnsubscribeTask();
	~FMqttUnsubscribeTask();
	
	char* sub;
};

struct FMqttPublishTask : public FMqttTask
{
	FMqttPublishTask();
	~FMqttPublishTask();
	
	char* topic;
	int payloadlen;
	void* payload;
	int qos;
	bool retain;
};

typedef TSharedPtr<FMqttSubscribeTask> FMqttSubscribeTaskPtr;
typedef TSharedPtr<FMqttUnsubscribeTask> FMqttUnsubscribeTaskPtr;
typedef TSharedPtr<FMqttPublishTask> FMqttPublishTaskPtr;
typedef TSharedPtr<FMqttTask> FMqttTaskPtr;