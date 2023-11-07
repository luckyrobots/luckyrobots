// Copyright (c) 2023 T4lus Development

#include "MqttClient.h"

#include "MqttDelegate.h"
#include "Utils/ConversionUtils.h"

#include "Async/Async.h"

UMqttClient::~UMqttClient()
{
	if(mqttSession != nil)
	{
		(MQTTSession*)CFBridgingRelease(mqttSession);
		mqttSession = nil;
	}
}

void UMqttClient::Connect(FMqttConnectionData connectionData, const FOnConnectDelegate& onConnectCallback)
{
	OnConnectDelegate = onConnectCallback;
	
	mqttSession.password = connectionData.Password.GetNSString();
	mqttSession.userName = connectionData.Login.GetNSString();

	[mqttSession connectWithConnectHandler:^(NSError *error) {
		if (error) {
			int errCode = error.code;
			FString errMsg = FString(error.localizedDescription);
			AsyncTask(ENamedThreads::GameThread, [=]() {
				OnErrorDelegate.ExecuteIfBound(errCode, errMsg);
			});
		}
	}];
}

void UMqttClient::Disconnect(const FOnDisconnectDelegate& onDisconnectCallback)
{
	OnDisconnectDelegate = onDisconnectCallback;
	
	[mqttSession disconnect];
}

void UMqttClient::Subscribe(FString topic, int qos)
{
	[mqttSession subscribeToTopic:topic.GetNSString() atLevel:ConversionUtils::ConvertIntToQosLevel(qos) subscribeHandler:^(NSError *error, NSArray<NSNumber *> *gQoss) {
		if (error) {
			int errCode = error.code;
			FString errMsg = FString(error.localizedDescription);
			AsyncTask(ENamedThreads::GameThread, [=]() {
				OnErrorDelegate.ExecuteIfBound(errCode, errMsg);
			});
		}
 	}];
}

void UMqttClient::Unsubscribe(FString topic)
{
	[mqttSession unsubscribeTopic:topic.GetNSString() unsubscribeHandler:^(NSError *error) {
		if (error) {
			int errCode = error.code;
			FString errMsg = FString(error.localizedDescription);
			AsyncTask(ENamedThreads::GameThread, [=]() {
				OnErrorDelegate.ExecuteIfBound(errCode, errMsg);
			});
		}
	}];
}

void UMqttClient::Publish(FMqttMessage message)
{
	[mqttSession publishData:[message.Message.GetNSString() dataUsingEncoding:NSUTF8StringEncoding] onTopic:message.Topic.GetNSString() 
		retain:message.Retain qos:ConversionUtils::ConvertIntToQosLevel(message.Qos)
		publishHandler:^(NSError *error) {
		if (error) {
			int errCode = error.code;
			FString errMsg = FString(error.localizedDescription);
			AsyncTask(ENamedThreads::GameThread, [=]() {
				OnErrorDelegate.ExecuteIfBound(errCode, errMsg);
			});
		}
	}];
}

void UMqttClient::Init(FMqttClientConfig configData)
{
	MQTTCFSocketTransport *transport = [[MQTTCFSocketTransport alloc] init];
	transport.host = configData.HostUrl.GetNSString();
	transport.port = configData.Port;
		
	MQTTSession* session = [[MQTTSession alloc] init];
	session.transport = transport;
	session.clientId = configData.ClientId.GetNSString();

	MqttDelegate* mqttDelegate = [[MqttDelegate alloc] init];

	mqttDelegate.onConnected = ^() {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnConnectDelegate.ExecuteIfBound();
		});
	};

	mqttDelegate.onDisconnected = ^() {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnDisconnectDelegate.ExecuteIfBound();
		});
	};

	mqttDelegate.onPublished = ^(int mid) {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnPublishDelegate.ExecuteIfBound(mid);
		});
	};

	mqttDelegate.onMessageReceived = ^(FMqttMessage message) {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnMessageDelegate.ExecuteIfBound(message);
		});
	};

	mqttDelegate.onSubscribed = ^(int mid, TArray<int> qos) {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnSubscribeDelegate.ExecuteIfBound(mid, qos);
		});
	};

	mqttDelegate.onUnsubscribed = ^(int mid) {
		AsyncTask(ENamedThreads::GameThread, [=]() {
			OnUnsubscribeDelegate.ExecuteIfBound(mid);
		});
	};

	session.delegate = mqttDelegate;

	mqttSession = (MQTTSession*)CFBridgingRetain(session);
}
