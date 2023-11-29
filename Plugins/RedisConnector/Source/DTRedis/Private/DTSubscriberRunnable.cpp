// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "DTSubscriberRunnable.h"
#include "DTRedisHead.h"
#include "DTRedisObject.h"

// 构造函数
CDTSubscriberRunnable::CDTSubscriberRunnable(UDTRedisObject* pDTRedisObject, const TArray<FString>& ArraySubKey)
{
    m_bStopping = false;

    m_pDTRedisObject = pDTRedisObject;
    m_pRedis = pDTRedisObject->GetRedis();
    m_pSubscriber = nullptr;

    m_ArraySubKey.Append(ArraySubKey);
}

// 析构函数
CDTSubscriberRunnable::~CDTSubscriberRunnable()
{
	m_bStopping = true;
}

// 初始化
bool CDTSubscriberRunnable::Init()
{
	m_bStopping = false;

	return true;
}

// 运行
uint32 CDTSubscriberRunnable::Run()
{
	// 线程计数器控制
	while (!m_bStopping)   
	{
        try
        {
            // 获取新的订阅对象
            Subscriber Sub = m_pRedis->subscriber();
            Sub.on_message([this](const std::string& channel, const std::string& msg) {
                    
                    m_pDTRedisObject->CallBackSubscriber(channel, msg);
                });

            // 注册订阅
            for ( FString Key : m_ArraySubKey )
            {
                Sub.subscribe(TCHAR_TO_UTF8(*Key));
            }

            // 保存订阅对象
            m_pSubscriber = &Sub;

            while (!m_bStopping)
            {
                Sub.consume();
            }
        }
        catch (...)
        {
            m_pSubscriber = nullptr;
        }
	}
	return 0;
}

// 停止
void CDTSubscriberRunnable::Stop()
{
	m_bStopping = true;    
    if (m_pSubscriber != nullptr)
    {
        m_pSubscriber->close();
        m_pSubscriber = nullptr;
    }
}
