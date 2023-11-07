// Copyright (c) 2023 T4lus Development

#include "ConversionUtils.h"

MQTTQosLevel ConversionUtils::ConvertIntToQosLevel(int qos)
{
	MQTTQosLevel qosLevel = MQTTQosLevelAtMostOnce;

	switch (qos)
	{
	case 0:
		qosLevel = MQTTQosLevelAtMostOnce;
		break;
	case 1:
		qosLevel = MQTTQosLevelAtLeastOnce;
		break;
	case 2:
		qosLevel = MQTTQosLevelExactlyOnce;
		break;
	default:
		UE_LOG(LogTemp, Warning, TEXT("MQTT => ConvertIntToQosLevel wrong input qos value"));
		break;
	}

	return qosLevel;
}

int ConversionUtils::GonvertQosLevelToInt(MQTTQosLevel qosLevel)
{
	int qos = 0;

	switch (qosLevel)
	{
	case MQTTQosLevelAtMostOnce:
		qos = 0;
		break;
	case MQTTQosLevelAtLeastOnce:
		qos = 1;
		break;
	case MQTTQosLevelExactlyOnce:
		qos = 2;
		break;
	default:
		UE_LOG(LogTemp, Warning, TEXT("MQTT => GonvertQosLevelToInt wrong input qosLevel value"));
		break;
	}

	return qos;
}