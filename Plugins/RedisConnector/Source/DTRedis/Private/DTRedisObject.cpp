// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "DTRedisObject.h"
#include "DTRedisHead.h"
#include "DTSubscriberRunnable.h"
#include "HAL/RunnableThread.h"
#include "Async/TaskGraphInterfaces.h"
#include "Async/Async.h"

// 当前对象指针
UDTRedisObject* UDTRedisObject::g_UDTRedisObject = nullptr;

// 析构函数
UDTRedisObject::~UDTRedisObject()
{
	// 清空上次连接数据
	Disconnect();
}

// 清空连接
void UDTRedisObject::ClearConnection()
{
	if (g_UDTRedisObject != nullptr)
	{
		g_UDTRedisObject->Disconnect();
	}
}

// 连接Redis
bool UDTRedisObject::Connect(const FString& Host, int Port, const FString& User, const FString& Password, int32 DBIndex, FString& ErrorMsg)
{
	// 清空上次连接数据
	Disconnect();

	// 连接属性
	ConnectionOptions connectionOptions;
	connectionOptions.host = TCHAR_TO_UTF8(*Host);
	connectionOptions.port = Port;
	connectionOptions.user = TCHAR_TO_UTF8(*User);
	connectionOptions.password = TCHAR_TO_UTF8(*Password);
	connectionOptions.db = DBIndex;

	// 连接池属性
	ConnectionPoolOptions poolOptions;
	poolOptions.size = 3;
	poolOptions.wait_timeout = std::chrono::milliseconds(100);

	try 
	{
		// 创建对象
		m_pRedisObject = Redis::NewRedis(connectionOptions, poolOptions);

		ErrorMsg = TEXT("Success");

		return true;
	}
	catch (const std::exception& err) 
	{
		ErrorMsg = UTF8_TO_TCHAR(err.what());

		return false;
	}
	catch (...) 
	{
		ErrorMsg = TEXT("unknown error");

		return false;
	}
}

// 断开连接
bool UDTRedisObject::Disconnect()
{
	try
	{
		SAFE_POINTER_FUNC(m_pSubscriberThread, Kill(true));
		SAFE_POINTER_DELETE(m_pSubscriberRunnable);
		SAFE_POINTER_DELETE(m_pSubscriberThread);
		Redis::DeleteRedis(m_pRedisObject);
		m_bSubscriber = false;

		return true;
	}
	catch (...)
	{
		return false;
	}
}

// 执行订阅
void UDTRedisObject::ExecuteSubscriber(const TArray<FString>& ArraySubKey)
{
	// 只执行一次
	if (m_bSubscriber || m_pRedisObject == nullptr)
	{
		return ;
	}
	
	// 设置状态
	m_bSubscriber = true;
	m_pSubscriberRunnable = new CDTSubscriberRunnable(this, ArraySubKey);
	m_pSubscriberThread = FRunnableThread::Create(m_pSubscriberRunnable, TEXT("CDTSubscriberRunnable"));
}

// 订阅线程回调
void UDTRedisObject::CallBackSubscriber(const std::string& Channel, const std::string& Message)
{
	FString BufferChannel(UTF8_TO_TCHAR(Channel.c_str()));
	FString BufferMessage(UTF8_TO_TCHAR(Message.c_str()));
	AsyncTask(ENamedThreads::GameThread, [this, BufferChannel, BufferMessage]()
	{
		if (m_SubscriberCallBack.IsBound())
		{
			m_SubscriberCallBack.Execute(BufferChannel, BufferMessage);
		}
	});
}

// 创建Redis
void UDTRedisObject::CreateRedis(EBP_Result& Result, FString& ErrorMsg, const FString& Host, int Port, const FString& User, const FString& Password, int32 DBIndex)
{
	// 没有对象
	if (g_UDTRedisObject == nullptr)
	{
		// 创建对象并初始化
		g_UDTRedisObject = NewObject<UDTRedisObject>();
		g_UDTRedisObject->AddToRoot();
	}

	// 构建连接
	if (g_UDTRedisObject->Connect(Host, Port, User, Password, DBIndex, ErrorMsg))
	{
		Result = EBP_Result::Success;
	}
	else
	{
		Result = EBP_Result::Failure;
	}

	return;
}

// 设置字段
void UDTRedisObject::RedisSet(const FString& Key, const FString& Value, int32 EffectiveTime, EBP_Result& Result, FString& ErrorMsg)
{
	REDIS_TRY_BEGIN;

	// 调用保存
	if (EffectiveTime < 0) { EffectiveTime = 0; }
	g_UDTRedisObject->GetRedis()->set(TCHAR_TO_UTF8(*Key), TCHAR_TO_UTF8(*Value), std::chrono::milliseconds(EffectiveTime));

	REDIS_TRY_END;
}

// 获取字段
void UDTRedisObject::RedisGet(const FString& Key, FString& Value)
{
	// 无效Redis
	if (g_UDTRedisObject == nullptr || g_UDTRedisObject->GetRedis() == nullptr)
	{
		return;
	}

	try
	{
		// 定义数据
		StringView svKey(TCHAR_TO_UTF8(*Key));

		// 调用读取
		OptionalString optionalString = g_UDTRedisObject->GetRedis()->get(svKey);
		Value = UTF8_TO_TCHAR(optionalString.value().c_str());
	}
	catch (...)
	{
		Value = TEXT("");
	}
}

// 删除字段
void UDTRedisObject::RedisDelete(const FString& Key, EBP_Result& Result, FString& ErrorMsg)
{
	REDIS_TRY_BEGIN;

	// 调用删除
	g_UDTRedisObject->GetRedis()->del(TCHAR_TO_UTF8(*Key));

	REDIS_TRY_END;
}

// 订阅消息
void UDTRedisObject::RedisSubscriber(const TArray<FString>& ChannelKey, FSubscriberCallBack CallBack, EBP_Result& Result, FString& ErrorMsg)
{
	REDIS_TRY_BEGIN;

	// 已经订阅
	if (g_UDTRedisObject->HasSubscriber())
	{
		REDIS_RETURN(EBP_Result::Failure, TEXT("Subscription can only be performed once"));
	}

	// 开启订阅
	g_UDTRedisObject->m_SubscriberCallBack = CallBack;
	g_UDTRedisObject->ExecuteSubscriber(ChannelKey);
	

	REDIS_TRY_END;
}

// 推送消息
void UDTRedisObject::RedisPublish(const FString& ChannelKey, const FString& Message, EBP_Result& Result, FString& ErrorMsg)
{
	REDIS_TRY_BEGIN;

	// 调用推送
	g_UDTRedisObject->GetRedis()->publish(TCHAR_TO_UTF8(*ChannelKey), TCHAR_TO_UTF8(*Message));

	REDIS_TRY_END;
}