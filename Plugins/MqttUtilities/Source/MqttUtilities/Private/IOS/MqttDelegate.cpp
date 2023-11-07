// Copyright (c) 2023 T4lus Development

#include "MqttDelegate.h"
#include "Utils/ConversionUtils.h"

@implementation MqttDelegate {

}

- (void)connected:(MQTTSession *)session
{
	if (_onConnected)
	{
		_onConnected();
	}
}

- (void)connectionClosed:(MQTTSession *)session
{
	if (_onDisconnected)
	{
		_onDisconnected();
	}
}

- (void)messageDelivered:(MQTTSession *)session msgID:(UInt16)msgID
{
	if (_onPublished)
	{
		_onPublished(msgID);
	}
}

- (void)newMessage:(MQTTSession *)session data:(NSData *)data onTopic:(NSString *)topic qos:(MQTTQosLevel)qos retained:(BOOL)retained mid:(unsigned int)mid 
{
	if (_onMessageReceived)
	{
		FMqttMessage message;

		NSString* dataStr = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];

		message.Message = FString(dataStr);
		message.Topic = FString(topic);
		message.Retain = retained;
		message.Qos = ConversionUtils::GonvertQosLevelToInt(qos);

		_onMessageReceived(message);
	}
}

- (void)subAckReceived:(MQTTSession *)session msgID:(UInt16)msgID grantedQoss:(NSArray<NSNumber*>*)qoss
{
	if (_onSubscribed)
	{
		TArray<int> qos;

		for (NSNumber *q in qoss)
		{
			qos.Add([q intValue]);
		}
		
		_onSubscribed(msgID, qos);
	}
}

- (void)unsubAckReceived:(MQTTSession *)session msgID:(UInt16)msgID
{
	if (_onUnsubscribed)
	{
		_onUnsubscribed(msgID);
	}
}

@end