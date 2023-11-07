// Copyright (c) 2023 T4lus Development

#include "MqttClientImpl.h"
#include "MqttRunnable.h"

MqttClientImpl::MqttClientImpl(const char* id) : mosqpp::mosquittopp(id)
{
}

MqttClientImpl::~MqttClientImpl()
{
}

void MqttClientImpl::on_connect(int rc)
{
	if (rc != 0)
	{
		return;
	}

	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Connected"));

	Task->OnConnect();
}

void MqttClientImpl::on_disconnect(int rc)
{
	if (rc != 0)
	{
		return;
	}

	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Disconnected"));

	Task->OnDisconnect();
}

void MqttClientImpl::on_publish(int mid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Message published"));

	Task->OnPublished(mid);
}

void MqttClientImpl::on_message(const mosquitto_message* src)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Message received"));

	FMqttMessage msg;

	msg.Topic = FString(src->topic);
	msg.Qos = src->qos;
	msg.Retain = src->retain;
	int PayloadLength = src->payloadlen;

	void* buffer = malloc(PayloadLength + 1);
	((char*)buffer)[PayloadLength] = 0;

	if (buffer != NULL)
	{
		memcpy(buffer, src->payload, PayloadLength);
	}

	msg.Message = FString(UTF8_TO_TCHAR(buffer));

	free(buffer);

	// Create a buffer to hold the payload without converting to FString
	TArray<uint8> Buffer;
	// Allocate memory for the buffer to hold the payload
	Buffer.SetNumZeroed(PayloadLength);
	if (PayloadLength > 0) {
		// Copy the payload to the buffer
		FMemory::Memcpy(Buffer.GetData(), src->payload, PayloadLength);
	}
	msg.MessageBuffer = Buffer;

	Task->OnMessage(msg);
}

void MqttClientImpl::on_subscribe(int mid, int qos_count, const int* granted_qos)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Subscribed"));

	TArray<int> qos;

	for (auto p = granted_qos; p < granted_qos + qos_count; ++p)
	{
		qos.Add(*p);
	}

	Task->OnSubscribe(mid, qos);
}

void MqttClientImpl::on_unsubscribe(int mid)
{
	UE_LOG(LogTemp, Warning, TEXT("MQTT => Impl: Unsubscribed"));

	Task->OnUnsubscribe(mid);
}
