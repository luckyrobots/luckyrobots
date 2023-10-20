// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#pragma once

#include "CoreMinimal.h"
#include "DTRedisHead.h"
#include "DTRedisObject.h"
#include "HAL/Runnable.h"

/**
 * 
 */
class DTREDIS_API CDTSubscriberRunnable : public FRunnable
{

private:
	bool						m_bStopping;						// 循环控制

private:
	class UDTRedisObject*		m_pDTRedisObject;					// Redis对象
	Redis*						m_pRedis;							// Redis对象连接
	Subscriber*					m_pSubscriber;						// 订阅对象
	
private:
	TArray<FString>				m_ArraySubKey;						// 订阅数组

public:
	// 构造函数
	CDTSubscriberRunnable(class UDTRedisObject * pDTRedisObject, const TArray<FString>& ArraySubKey);
	// 析构函数
	~CDTSubscriberRunnable();

public:
	// 初始化
	virtual bool Init() override;
	// 运行
	virtual uint32 Run() override;
	// 停止
	virtual void Stop() override;
};
