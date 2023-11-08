// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"

#include "Entities/MqttClientConfig.h"
#include "Entities/MqttConnectionData.h"
#include "Interface/MqttClientInterface.h"


#include "MqttComponent.generated.h"


UCLASS( ClassGroup=(Custom), meta=(BlueprintSpawnableComponent) )
class CONTROLLABLE_PAWN_API UMqttComponent : public UActorComponent
{
	GENERATED_BODY()

public:	

	UMqttComponent();
	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

public:

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FMqttClientConfig MqttConfig;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FMqttConnectionData MqttConnectionData;

private:
	TScriptInterface<IMqttClientInterface> MqttInterface;

protected:
	UPROPERTY()
	FOnConnectDelegate OnConnectDelegate;

	void OnConnected();
};
