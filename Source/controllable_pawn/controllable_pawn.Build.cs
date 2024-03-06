// Fill out your copyright notice in the Description page of Project Settings.

using UnrealBuildTool;

public class controllable_pawn : ModuleRules
{
	public controllable_pawn(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicIncludePaths.AddRange(
           new string[] {
                "controllable_pawn"
           }
       );

        PrivateIncludePaths.AddRange(
            new string[] {
            }
        );

        PublicDependencyModuleNames.AddRange(new string[] { 
            "Core", 
            "CoreUObject", 
            "Engine", 
            "InputCore" 
        });


    }
}
