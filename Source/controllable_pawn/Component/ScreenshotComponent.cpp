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
	TargetGamma = 2.f;

	PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_LegacySceneCapture;
	CompositeMode = ESceneCaptureCompositeMode::SCCM_Overwrite;
	CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
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
	//TextureRenderTarget->RenderTargetFormat = ETextureRenderTargetFormat::RTF_RGBA8;
	TextureRenderTarget->bGPUSharedFlag = true;

	USceneCaptureComponent2D* CaptureScene = NewObject<USceneCaptureComponent2D>(this, USceneCaptureComponent2D::StaticClass());
	CaptureScene->AttachToComponent(Camera,FAttachmentTransformRules::KeepRelativeTransform);
	CaptureScene->PrimitiveRenderMode = PrimitiveRenderMode;
	CaptureScene->CompositeMode = CompositeMode;
	CaptureScene->CaptureSource = CaptureSource;
	CaptureScene->TextureTarget = TextureRenderTarget;
	CaptureScene->TextureTarget->TargetGamma = TargetGamma;
	CaptureScene->bUseRayTracingIfEnabled = bUseRayTracingIfEnabled;

	if (PostProcessMaterial)
	{
		CaptureScene->PostProcessSettings.AddBlendable(PostProcessMaterial, 1);
	}

	CaptureScene->CaptureScene();

	IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(FName("ImageWrapper"));
	TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);

	TArray<FColor> Image;
	Image.AddZeroed(CaptureScene->TextureTarget->SizeX * CaptureScene->TextureTarget->SizeY);

	FTextureRenderTargetResource* RenderTargetResource;
	RenderTargetResource = CaptureScene->TextureTarget->GameThread_GetRenderTargetResource();

	FReadSurfaceDataFlags ReadSurfaceDataFlags;
	ReadSurfaceDataFlags.SetLinearToGamma(false);

	RenderTargetResource->ReadPixels(Image, ReadSurfaceDataFlags);

	if (!ImageWrapper.IsValid())
	{
		return false;
	}

	if (!ImageWrapper->SetRaw(Image.GetData(), Image.GetAllocatedSize(), CaptureScene->TextureTarget->SizeX, CaptureScene->TextureTarget->SizeY, ERGBFormat::BGRA, 8))
	{
		return false;
	}

	OutData = ImageWrapper->GetCompressed();

	CaptureScene->DestroyComponent();

	return true;
}