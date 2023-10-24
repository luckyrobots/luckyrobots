// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "DTRedisEditor.h"
#include "DTRedisObject.h"

#define LOCTEXT_NAMESPACE "FDTRedisEditorModule"

// 系统开始运行
void FDTRedisEditorModule::StartupModule()
{
	FEditorDelegates::PreBeginPIE.AddRaw(this, &FDTRedisEditorModule::OnPreBeginPIE);
	FEditorDelegates::EndPIE.AddRaw(this, &FDTRedisEditorModule::OnEndPIE);
}

// 系统结束运行
void FDTRedisEditorModule::ShutdownModule()
{

}
// PIE开始
void FDTRedisEditorModule::OnPreBeginPIE(const bool bIsSimulatingInEditor)
{
}

// PIE结束
void FDTRedisEditorModule::OnEndPIE(const bool bIsSimulatingInEditor)
{
	UDTRedisObject::ClearConnection();
}


#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FDTRedisEditorModule, DTRedisEditor)