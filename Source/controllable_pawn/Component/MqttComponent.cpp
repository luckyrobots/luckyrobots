// Fill out your copyright notice in the Description page of Project Settings.


#include "Component/MqttComponent.h"

#include "MqttUtilitiesBPL.h"

UMqttComponent::UMqttComponent()
{
	PrimaryComponentTick.bCanEverTick = true;

	MqttConnectionData.Login = "guest";
	MqttConnectionData.Password = "guest";

	OnConnectDelegate.BindDynamic(this, &UMqttComponent::OnConnected);
	
}

void UMqttComponent::BeginPlay()
{
	Super::BeginPlay();
	
	MqttInterface = UMqttUtilitiesBPL::CreateMqttClient(MqttConfig);
	if (MqttInterface)
	{
		MqttInterface->Connect(MqttConnectionData, OnConnectDelegate);
	}

	FMqttMessage Message;
	Message.Topic = "Test Topic";
	Message.Message = "Test Message";
	Message.Retain = false;
	Message.Qos = 0;

	MqttInterface->Publish(Message);
}



void UMqttComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

}

void UMqttComponent::OnConnected()
{

}