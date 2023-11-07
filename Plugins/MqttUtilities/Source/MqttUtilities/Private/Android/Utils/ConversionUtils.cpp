// Copyright (c) 2023 T4lus Development

#include "ConversionUtils.h"

jstring ConversionUtils::GetJavaString(FString string)
{
	JNIEnv*	JEnv = AndroidJavaEnv::GetJavaEnv();
	jstring local = JEnv->NewStringUTF(TCHAR_TO_UTF8(*string));
	jstring result = (jstring)JEnv->NewGlobalRef(local);
	JEnv->DeleteLocalRef(local);
	return result;
}

jbyteArray ConversionUtils::ConvertToJByteArray(const TArray<uint8>& byteArray)
{
	JNIEnv* Env = FAndroidApplication::GetJavaEnv();

	jbyteArray javaByteArray = (jbyteArray)Env->NewByteArray(byteArray.Num());

	jbyte* javaByteArrayPtr = (jbyte*)malloc(byteArray.Num() * sizeof(jbyte));

	for (int i = 0; i < byteArray.Num(); ++i)
	{
		javaByteArrayPtr[i] = byteArray[i];
	}

	Env->SetByteArrayRegion(javaByteArray, 0, byteArray.Num(), javaByteArrayPtr);

	free(javaByteArrayPtr);

	return javaByteArray;
}

TArray<int> ConversionUtils::ConvertToIntArray(jintArray javaArray)
{
	TArray<int> intArray;

	JNIEnv* Env = FAndroidApplication::GetJavaEnv();

	jint* javaInt = Env->GetIntArrayElements(javaArray, 0);

	int length = Env->GetArrayLength(javaArray);

	for (int i = 0; i < length; i++)
	{
		intArray.Add(javaInt[i]);
	}

	return intArray;
}

TArray<uint8> ConversionUtils::ConvertToByteArray(jbyteArray javaArray)
{
	TArray<uint8> byteArray;

	JNIEnv* Env = FAndroidApplication::GetJavaEnv();

	jbyte* javaByte = Env->GetByteArrayElements(javaArray, 0);

	int length = Env->GetArrayLength(javaArray);

	for (int i = 0; i < length; i++)
	{
		byteArray.Add(javaByte[i]);
	}

	return byteArray;
}

FJavaClassObject* ConversionUtils::ConvertToJavaConnectionData(FMqttConnectionData connectionData)
{
	FJavaClassObject* javaConnectionData = new FJavaClassObject("org/eclipse/paho/client/mqttv3/MqttConnectOptions", "()V");
	FJavaClassMethod setUserNameMethod =  javaConnectionData->GetClassMethod("setUserName", "(Ljava/lang/String;)V");
	FJavaClassMethod setPasswordMethod =  javaConnectionData->GetClassMethod("setPassword", "([C)V");

	javaConnectionData->CallMethod<void>(setUserNameMethod, GetJavaString(connectionData.Login));

	jstring javaPassword = GetJavaString(connectionData.Password);
	JNIEnv*	Env = AndroidJavaEnv::GetJavaEnv();
	jclass cls = Env->GetObjectClass(javaPassword);
	jmethodID mid = Env->GetMethodID(cls, "toCharArray", "()[C");
	jcharArray passChars = (jcharArray) Env->CallObjectMethod(javaPassword, mid);

	javaConnectionData->CallMethod<void>(setPasswordMethod, passChars);
	
	return javaConnectionData;
}

FJavaClassObject * ConversionUtils::ConvertToJavaMessage(FMqttMessage message)
{
	jstring javaMessageString = GetJavaString(message.Message);

	JNIEnv*	Env = AndroidJavaEnv::GetJavaEnv();
	jclass cls = Env->GetObjectClass(javaMessageString);
	jmethodID mid = Env->GetMethodID(cls, "getBytes", "()[B");
	jbyteArray javaArray = (jbyteArray) Env->CallObjectMethod(javaMessageString, mid);

	FJavaClassObject* javaMessage = new FJavaClassObject("org/eclipse/paho/client/mqttv3/MqttMessage", "([B)V", javaArray);

	FJavaClassMethod setQosMethod =  javaMessage->GetClassMethod("setQos", "(I)V");
	FJavaClassMethod setRetainedMethod =  javaMessage->GetClassMethod("setRetained", "(Z)V");

	return javaMessage;
}

FMqttMessage ConversionUtils::ConvertFromJavaMessage(jstring topic, jobject javaMessage)
{
	bool bIsOptional = false;
	FMqttMessage message;

	message.Topic = FromJavaString(topic);

	JNIEnv*	Env = AndroidJavaEnv::GetJavaEnv();
	jclass Class = Env->GetObjectClass(javaMessage);

	jmethodID GetPayloadMethodId = FJavaWrapper::FindMethod(Env, Class, "getPayload", "()[B", bIsOptional);
	jbyteArray javaPayload = (jbyteArray) Env->CallObjectMethod(javaMessage, GetPayloadMethodId);

	jclass helperClass = Env->FindClass("com/ninevastudios/mqttdemo/MqttHelper");
	jmethodID convertArrayMethod = FJavaWrapper::FindStaticMethod(Env, helperClass, "stringFromByteArray", "([B)Ljava/lang/String;", bIsOptional);
	jstring javaPayloadString = (jstring) Env->CallStaticObjectMethod(helperClass, convertArrayMethod, javaPayload);
	message.Message = FromJavaString(javaPayloadString);

	jmethodID GetQosMethodId = FJavaWrapper::FindMethod(Env, Class, "getQos", "()I", bIsOptional);
	message.Qos = Env->CallIntMethod(javaMessage, GetQosMethodId);

	jmethodID GetRetainedMethodId = FJavaWrapper::FindMethod(Env, Class, "isRetained", "()Z", bIsOptional);
	message.Retain = Env->CallBooleanMethod(javaMessage, GetRetainedMethodId);

	return message;
}

FString ConversionUtils::FromJavaString(jstring javaString)
{
	JNIEnv*	Env = AndroidJavaEnv::GetJavaEnv();
	const char * UTFString = Env->GetStringUTFChars(javaString, nullptr);
	FString Result(UTF8_TO_TCHAR(UTFString));
	Env->ReleaseStringUTFChars(javaString, UTFString);

	return Result;
}
