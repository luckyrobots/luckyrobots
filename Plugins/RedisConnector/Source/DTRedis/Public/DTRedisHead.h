// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#pragma once

#include "redis.h"

#if PLATFORM_WINDOWS
#include "redis.h"
#elif PLATFORM_LINUX
#include "redis.h"
#include <stdexcept>
#endif 

using namespace sw::redis;

#if PLATFORM_WINDOWS
#define REDIS_TRY_BEGIN															\
try{																			\
	if (g_UDTRedisObject == nullptr || g_UDTRedisObject->GetRedis() == nullptr) \
	{																			\
		throw std::exception("not created");									\
	}
#elif PLATFORM_LINUX
#define REDIS_TRY_BEGIN															\
try{																			\
	if (g_UDTRedisObject == nullptr || g_UDTRedisObject->GetRedis() == nullptr) \
	{																			\
		throw std::logic_error("not created");									\
	}
#endif 



#define REDIS_TRY_END															\
	ErrorMsg = TEXT("Success");	Result = EBP_Result::Success; return; 			\
}																				\
catch (const std::exception& err) 												\
{																				\
	ErrorMsg = UTF8_TO_TCHAR(err.what()); 										\
	Result = EBP_Result::Failure;												\
	return; 																	\
}																				\
catch (...)																		\
{																				\
	ErrorMsg = TEXT("unknown error");											\
	Result = EBP_Result::Failure;												\
	return; 																	\
}

#define REDIS_RETURN(R, E)														\
{																				\
	ErrorMsg = E;																\
	Result = R;																	\
	return; 																	\
}

// 安全指针调用
#define SAFE_POINTER_FUNC(p, func) 												\
{ 																				\
	if(p) 																		\
	{																			\
		p->func;																\
	} 																			\
}											
#define SAFE_POINTER_DELETE(p) 													\
{ 																				\
	if(p) 																		\
	{ 																			\
		delete p; 																\
		p = NULL;																\
	} 																			\
}											