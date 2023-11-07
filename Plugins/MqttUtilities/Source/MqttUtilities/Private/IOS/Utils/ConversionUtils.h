// Copyright (c) 2023 T4lus Development

#pragma once

#import <MQTTClient/MQTTClient.h>

class ConversionUtils
{
public:

	static MQTTQosLevel ConvertIntToQosLevel(int qos);
	static int GonvertQosLevelToInt(MQTTQosLevel qosLevel);
};