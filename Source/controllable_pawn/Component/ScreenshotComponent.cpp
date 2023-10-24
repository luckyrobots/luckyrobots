// Fill out your copyright notice in the Description page of Project Settings.


#include "ScreenshotComponent.h"

#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetRenderingLibrary.h"

#include "Subsystem/DatabaseSubsystem.h"

UScreenshotComponent::UScreenshotComponent()
{
	PrimaryComponentTick.bCanEverTick = true;

	ScreenshotSize = FVector2D(640, 480);
}

void UScreenshotComponent::BeginPlay()
{
	Super::BeginPlay();

}

void UScreenshotComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);


}

void UScreenshotComponent::TakeScreenShot(UCameraComponent* LeftCamera, UCameraComponent* RightCamera)
{
	TArray<uint8> LeftCameraData;
	TArray<uint8> RightCameraData;

	if (LeftCamera) 
	{
		ProcessCamera(LeftCamera, "LeftCamera", LeftCameraData);
	}

	if (RightCamera)
	{
		ProcessCamera(RightCamera, "RightCamera", RightCameraData);
	}

	UGameInstance* GameInstance = UGameplayStatics::GetGameInstance(this);
	UDatabaseSubsystem* DatabaseSubsystem = GameInstance->GetSubsystem<UDatabaseSubsystem>();
	DatabaseSubsystem->SaveScreenshot(LeftCameraData, RightCameraData);
}

bool UScreenshotComponent::ProcessCamera(UCameraComponent* Camera, FString TextureName, TArray<uint8>& OutData)
{
	UTextureRenderTarget2D* TextureRenderTarget = NewObject<UTextureRenderTarget2D>();
	TextureRenderTarget->InitAutoFormat(256, 256);
	TextureRenderTarget->InitCustomFormat(ScreenshotSize.X, ScreenshotSize.Y, PF_B8G8R8A8, true);
	TextureRenderTarget->RenderTargetFormat = ETextureRenderTargetFormat::RTF_RGBA8;
	TextureRenderTarget->bGPUSharedFlag = true;

	USceneCaptureComponent2D* CaptureScene = NewObject<USceneCaptureComponent2D>(this, USceneCaptureComponent2D::StaticClass());
	CaptureScene->AttachToComponent(Camera,FAttachmentTransformRules::KeepRelativeTransform);
	CaptureScene->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_LegacySceneCapture;
	CaptureScene->CompositeMode = ESceneCaptureCompositeMode::SCCM_Overwrite;
	CaptureScene->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	CaptureScene->TextureTarget = TextureRenderTarget;
	CaptureScene->CaptureScene();

	UTexture2D* Aux2DTex = CaptureScene->TextureTarget->ConstructTexture2D(this, TextureName, EObjectFlags::RF_NoFlags, CTF_DeferCompression);
	Aux2DTex->CompressionSettings = TextureCompressionSettings::TC_Default;
	Aux2DTex->SRGB = 0;
#if WITH_EDITORONLY_DATA
	Aux2DTex->MipGenSettings = TextureMipGenSettings::TMGS_NoMipmaps;
#endif
	Aux2DTex->UpdateResource();

	FColor* FormatedImageData = NULL;
	Aux2DTex->GetPlatformData()->Mips[0].BulkData.GetCopy((void**)&FormatedImageData);

	IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(FName("ImageWrapper"));
	TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);

	if (!ImageWrapper.IsValid())
	{
		return false;
	}

	if (!ImageWrapper->SetRaw(&FormatedImageData[0], CaptureScene->TextureTarget->SizeX * CaptureScene->TextureTarget->SizeY * sizeof(FColor), CaptureScene->TextureTarget->SizeX, CaptureScene->TextureTarget->SizeY, ERGBFormat::BGRA, 8))
	{
		return false;
	}

	OutData = ImageWrapper->GetCompressed(90);

	CaptureScene->DestroyComponent();

	return true;
}