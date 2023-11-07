// Copyright (c) 2023 T4lus Development

#pragma once

#include "Android/AndroidJNI.h"
#include "Android/AndroidApplication.h"
#include "Android/AndroidJava.h"

#include "Entities/MqttConnectionData.h"
#include "Entities/MqttMessage.h"

class ConversionUtils
{

public:
	static jstring GetJavaString(FString string);
	static jbyteArray ConvertToJByteArray(const TArray<uint8>& byteArray);
	static TArray<int> ConvertToIntArray(jintArray javaArray);	
	static TArray<uint8> ConvertToByteArray(jbyteArray javaArray);
	static FJavaClassObject* ConvertToJavaConnectionData(FMqttConnectionData connectionData);
	static FJavaClassObject* ConvertToJavaMessage(FMqttMessage message);
	static FMqttMessage ConvertFromJavaMessage(jstring topic, jobject javaMessage);
	static FString FromJavaString(jstring javaString);
};