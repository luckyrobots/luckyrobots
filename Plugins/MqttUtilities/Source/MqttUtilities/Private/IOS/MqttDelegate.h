// Copyright (c) 2023 T4lus Development

#pragma once

#include "Entities/MqttMessage.h"

#import <MQTTClient/MQTTClient.h>

@interface MqttDelegate : NSObject<MQTTSessionDelegate>

@property(nonatomic, copy) void (^onConnected)();
@property(nonatomic, copy) void (^onDisconnected)();
@property(nonatomic, copy) void (^onPublished)(int mid);
@property(nonatomic, copy) void (^onMessageReceived)(FMqttMessage message);
@property(nonatomic, copy) void (^onSubscribed)(int mid, TArray<int> qos);
@property(nonatomic, copy) void (^onUnsubscribed)(int mid);

@end