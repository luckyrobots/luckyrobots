// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "DTRedisHead.h"
#include "DTRedisObject.generated.h"

UENUM()
enum class EBP_Result : uint8
{
	Success,
	Failure,
};

/**
 * 
 */
UCLASS()
class DTREDIS_API UDTRedisObject : public UObject
{
	GENERATED_BODY()

private:
	Redis *							m_pRedisObject = nullptr;			// Redis对象连接
	bool							m_bSubscriber = false;				// 已经订阅

private:
	FRunnableThread *				m_pSubscriberThread = nullptr;		// 订阅线程管理
	class CDTSubscriberRunnable *	m_pSubscriberRunnable = nullptr;	// 订阅线程
	

private:
	static UDTRedisObject*	g_UDTRedisObject;					// 当前对象指针

public:
	// 代理回调
	DECLARE_DYNAMIC_DELEGATE_TwoParams(FSubscriberCallBack, const FString&, Channel, const FString&, Message);
	FSubscriberCallBack				m_SubscriberCallBack;

public:
	// 构造函数
	~UDTRedisObject();

	// 清空数据
public:
	// 清空连接
	static void ClearConnection();

public:
	// 获取Reis指针
	Redis* GetRedis() { return m_pRedisObject; }
	// 返回是否订阅
	bool HasSubscriber() { return m_bSubscriber; }

public:
	// 连接Redis
	bool Connect(const FString& Host, int Port, const FString& User, const FString& Password, int32 DBIndex, FString& ErrorMsg);
	// 断开连接
	bool Disconnect();
	// 执行订阅
	void ExecuteSubscriber(const TArray<FString>& ArraySubKey);
	// 订阅线程回调
	void CallBackSubscriber(const std::string& Channel, const std::string& Message);

public:
	// Create Redis Connect
	UFUNCTION(BlueprintCallable, meta = (ExpandEnumAsExecs = "Result"), Category = "DT Redis")
	static void CreateRedis(EBP_Result& Result, FString& ErrorMsg, const FString& Host, int Port = 6379, const FString& User = FString(TEXT("default")), const FString& Password = FString(TEXT("")), int32 DBIndex = 0);

	// Set Field
	UFUNCTION(BlueprintCallable, meta = (ExpandEnumAsExecs = "Result", AdvancedDisplay="EffectiveTime"), Category = "DT Redis")
	static void RedisSet(const FString& Key, const FString& Value, int32 EffectiveTime, EBP_Result& Result, FString& ErrorMsg);

	// Get Field
	UFUNCTION(BlueprintPure, Category = "DT Redis")
	static void RedisGet(const FString& Key, FString& Value);

	// Delete Field
	UFUNCTION(BlueprintCallable, meta = (ExpandEnumAsExecs = "Result"), Category = "DT Redis")
	static void RedisDelete(const FString& Key, EBP_Result& Result, FString& ErrorMsg);

	// Subscribe to a channel
	UFUNCTION(BlueprintCallable, meta = (ExpandEnumAsExecs = "Result"), Category = "DT Redis")
	static void RedisSubscriber(const TArray<FString>& ChannelKey, FSubscriberCallBack CallBack, EBP_Result& Result, FString& ErrorMsg);

	// push channel message
	UFUNCTION(BlueprintCallable, meta = (ExpandEnumAsExecs = "Result"), Category = "DT Redis")
	static void RedisPublish(const FString& ChannelKey, const FString& Message, EBP_Result& Result, FString& ErrorMsg);
};
