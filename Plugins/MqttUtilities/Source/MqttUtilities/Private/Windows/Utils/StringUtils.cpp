// Copyright (c) 2023 T4lus Development

#include "StringUtils.h"

char* StringUtils::CopyString(FString str)
{
	auto StringCaster = StringCast<ANSICHAR>(static_cast<const TCHAR*>(*str));
	const char* originalStr = StringCaster.Get();
	
	char *copyStr;
	size_t str_len;

	if (!originalStr)
	{
		return nullptr;
	}
	
	str_len = strlen(originalStr) + 1;
	
	if (nullptr == (copyStr = (char*)malloc(str_len)))
	{
		return nullptr;
	}	
	
	memcpy(copyStr, originalStr, str_len);

	return copyStr;
}