// Copyright Plasma Labs, 2023. All Rights Reserved.

#include "ImgSeg.h"
#include "ImgSegStyle.h"
#include "ImgSegCommands.h"
#include "DirectoryPickerWidget.h"
#include "LevelEditor.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Input/SButton.h"
#include "ToolMenus.h"

#include "Kismet/GameplayStatics.h"
#include "Engine/StaticMeshActor.h"
#include "Framework/SlateDelegates.h"
#include "Delegates/DelegateSignatureImpl.inl"


#include "AssetRegistry/AssetRegistryModule.h"
#include "PackageTools.h"
#include <ImgSegBP/Public/SwitchMaterials.h>
#include <ImgSegBP/Public/TakeCaptures.h>
#include <ImgSegBP/Public/ImgSegBP.h>




static const FName ImgSegTabName("Image Segmentation Tool");

#define LOCTEXT_NAMESPACE "FImgSegModule"


void FImgSegModule::StartupModule()
{
	FImgSegStyle::Initialize();
	FImgSegStyle::ReloadTextures();

	FImgSegCommands::Register();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FImgSegCommands::Get().OpenPluginWindow,
		FExecuteAction::CreateRaw(this, &FImgSegModule::PluginButtonClicked),
		FCanExecuteAction());

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FImgSegModule::RegisterMenus));

	FGlobalTabmanager::Get()->RegisterNomadTabSpawner(ImgSegTabName, FOnSpawnTab::CreateRaw(this, &FImgSegModule::OnSpawnPluginTab))
		.SetDisplayName(LOCTEXT("FImgSegTabTitle", "Image Segmentation Tool"))
		.SetMenuType(ETabSpawnerMenuType::Hidden);
}

void FImgSegModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.

	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FImgSegStyle::Shutdown();

	FImgSegCommands::Unregister();

	FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(ImgSegTabName);
}



TSharedRef<SDockTab> FImgSegModule::OnSpawnPluginTab(const FSpawnTabArgs& SpawnTabArgs)
{

	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
				.Padding(10, 5)
				.AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
				[
					SNew(STextBlock)
					.Text(FText::FromString("Select Data directory"))
				]
			+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				[
					SNew(SDirectoryPicker)
					.Directory(SelectedDirectory)
					.OnDirectoryChanged_Raw(this, &FImgSegModule::OnDirectoryChanged)
				]
				]
			+ SVerticalBox::Slot()
				.Padding(10, 5)
				.AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.VAlign(VAlign_Top)
				[
					SNew(STextBlock)
					.Text(FText::FromString("Capture Delay"))
				]
			+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				[
					SNew(SNumericEntryBox<float>)
					.MinValue(0)
					.Value_Raw(this, &FImgSegModule::GetCaptureDelay)
					.OnValueChanged_Raw(this, &FImgSegModule::CaptureDelayChanged)
				]
				]
			+ SVerticalBox::Slot()
				.Padding(10, 5)
				.AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.VAlign(VAlign_Top)
				[
					SNew(STextBlock)
					.Text(FText::FromString("Capture number"))
				]
			+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				[
					SNew(SNumericEntryBox<int32>)
					.MinValue(0)
					.Value_Raw(this, &FImgSegModule::GetCaptureNumber)
					.OnValueChanged_Raw(this, &FImgSegModule::CaptureNumberChanged)
				]
				]
			+ SVerticalBox::Slot()
				.Padding(10, 5)
				.AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.VAlign(VAlign_Top)
				[
					SNew(STextBlock)
					.Text(FText::FromString("Take Captures"))
				]
			+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				[
					SNew(SButton)
					.Text(FText::FromString("Start"))
					.OnClicked_Raw(this, &FImgSegModule::OnTakeCapturesButtonClick)
		]
		]
		];
}


FReply FImgSegModule::OnMakePostProcessButtonClick()
{
	USwitchMaterials* SwitchMaterials = NewObject<USwitchMaterials>();
	SwitchMaterials->ApplyStencilValues(false);
	return FReply::Handled();
}

FReply FImgSegModule::OnTakeCapturesButtonClick()
{
	if (isTakingCaptures == false) {
		isTakingCaptures = true;
	}
	else {
		isTakingCaptures = false;
	}
	UTakeCaptures* TakeCaptures = NewObject<UTakeCaptures>();
	TakeCaptures->AddToRoot();
	TakeCaptures->TakeCaptures(CaptureNumber, CaptureDelay, SelectedDirectory);


	USwitchMaterials* SwitchMaterials = NewObject<USwitchMaterials>();
	// find a way not to redo it all again and just save the tmap
	SwitchMaterials->ApplyStencilValues(true);
	SwitchMaterials->WriteMapToFile(SelectedDirectory);
	return FReply::Handled();
}


void FImgSegModule::OnDirectoryChanged(const FString& Directory)
{
	SelectedDirectory = Directory;
}

void FImgSegModule::CaptureDelayChanged(float value)
{
	CaptureDelay = value;
}

TOptional<float> FImgSegModule::GetCaptureDelay() const
{
	return CaptureDelay;
}

void FImgSegModule::CaptureNumberChanged(int32 value)
{
	CaptureNumber = value;
}

TOptional<int32> FImgSegModule::GetCaptureNumber() const
{
	return CaptureNumber;
}



void FImgSegModule::PluginButtonClicked()
{
	FGlobalTabmanager::Get()->TryInvokeTab(ImgSegTabName);
}

void FImgSegModule::RegisterMenus()
{
	// Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
	FToolMenuOwnerScoped OwnerScoped(this);

	{
		UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Window");
		{
			FToolMenuSection& Section = Menu->FindOrAddSection("WindowLayout");
			Section.AddMenuEntryWithCommandList(FImgSegCommands::Get().OpenPluginWindow, PluginCommands);
		}
	}

	{
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");
		{
			FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("Settings");
			{
				FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FImgSegCommands::Get().OpenPluginWindow));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FImgSegModule, ImgSeg)