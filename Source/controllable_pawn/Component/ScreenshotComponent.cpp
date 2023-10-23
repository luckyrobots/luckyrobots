// Fill out your copyright notice in the Description page of Project Settings.


#include "ScreenshotComponent.h"

#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Kismet/GameplayStatics.h"

#include "Subsystem/DatabaseSubsystem.h"

UScreenshotComponent::UScreenshotComponent()
{
	PrimaryComponentTick.bCanEverTick = true;

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
		ProcessCamera(LeftCamera, LeftCameraData);
	}

	if (RightCamera)
	{
		ProcessCamera(RightCamera, RightCameraData);
	}

	UGameInstance* GameInstance = UGameplayStatics::GetGameInstance(this);
	UDatabaseSubsystem* DatabaseSubsystem = GameInstance->GetSubsystem<UDatabaseSubsystem>();

	DatabaseSubsystem->SaveScreenshot(LeftCameraData, RightCameraData);
}

bool UScreenshotComponent::ProcessCamera(UCameraComponent* Camera, TArray<uint8>& OutData)
{
	UTextureRenderTarget2D* TextureRenderTarget = NewObject<UTextureRenderTarget2D>();
	TextureRenderTarget->InitAutoFormat(256, 256);
	TextureRenderTarget->InitCustomFormat(640, 480, PF_B8G8R8A8, true);
	TextureRenderTarget->RenderTargetFormat = ETextureRenderTargetFormat::RTF_RGBA8;
	TextureRenderTarget->ClearColor = FLinearColor::White;
	TextureRenderTarget->bGPUSharedFlag = true;

	USceneCaptureComponent2D* CaptureScene = NewObject<USceneCaptureComponent2D>(this, USceneCaptureComponent2D::StaticClass());
	CaptureScene->AttachToComponent(Camera,FAttachmentTransformRules::KeepRelativeTransform);
	CaptureScene->bCaptureEveryFrame = true;
	CaptureScene->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_LegacySceneCapture;
	CaptureScene->CompositeMode = ESceneCaptureCompositeMode::SCCM_Overwrite;
	CaptureScene->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	CaptureScene->TextureTarget = TextureRenderTarget;

	UE_LOG(LogTemp, Log, TEXT("Camera Position %s"), *Camera->GetComponentLocation().ToString());
	UE_LOG(LogTemp, Log, TEXT("Capture Position %s"), *CaptureScene->GetComponentLocation().ToString());

	UE_LOG(LogTemp, Log, TEXT("Camera Rotation %s"), *Camera->GetComponentRotation().ToString());
	UE_LOG(LogTemp, Log, TEXT("Capture Rotation %s"), *CaptureScene->GetComponentRotation().ToString());


	UTexture2D* Aux2DTex = TextureRenderTarget->ConstructTexture2D(this, "AlphaTex", EObjectFlags::RF_NoFlags, CTF_DeferCompression);
	Aux2DTex->CompressionSettings = TextureCompressionSettings::TC_VectorDisplacementmap;

#if WITH_EDITORONLY_DATA
	Aux2DTex->MipGenSettings = TextureMipGenSettings::TMGS_NoMipmaps;
#endif

	Aux2DTex->SRGB = 0;
	Aux2DTex->UpdateResource();

	FColor* FormatedImageData = NULL;
	Aux2DTex->GetPlatformData()->Mips[0].BulkData.GetCopy((void**)&FormatedImageData);

	IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(FName("ImageWrapper"));
	TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::JPEG);

	if (!ImageWrapper.IsValid())
	{
		return false;
	}

	if (!ImageWrapper->SetRaw(&FormatedImageData[0], TextureRenderTarget->SizeX * TextureRenderTarget->SizeY * sizeof(FColor), TextureRenderTarget->SizeX, TextureRenderTarget->SizeY, ERGBFormat::BGRA, 8))
	{
		return false;
	}

	OutData = ImageWrapper->GetCompressed(90);
	return true;
}