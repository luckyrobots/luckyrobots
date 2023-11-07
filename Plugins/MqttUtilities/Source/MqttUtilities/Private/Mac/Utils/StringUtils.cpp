// Copyright (c) 2023 T4lus Development

#include "StringUtils.h"

char* StringUtils::CopyString(FString str)
{
	const char* originalStr = TCHAR_TO_ANSI(*str);
	
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