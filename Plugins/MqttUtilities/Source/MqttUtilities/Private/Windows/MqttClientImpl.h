// Copyright (c) 2023 T4lus Development

#pragma once

#include <mosquittopp.h>

class FMqttRunnable;

class MqttClientImpl : public mosqpp::mosquittopp
{
public:

	MqttClientImpl(const char* id);
	~MqttClientImpl();

	void on_connect(int rc) override;
	void on_disconnect(int rc) override;
	void on_publish(int mid) override;
	void on_message(const struct mosquitto_message * message) override;
	void on_subscribe(int mid, int qos_count, const int* granted_qos) override;
	void on_unsubscribe(int mid) override;

	FMqttRunnable* Task;
};