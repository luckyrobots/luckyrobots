// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

using UnrealBuildTool;

public class DTRedisEditor : ModuleRules
{
	public DTRedisEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		
		PublicIncludePaths.AddRange(
			new string[] 
				{
				}
			);
				
		
		PrivateIncludePaths.AddRange(
			new string[] 
				{
				}
			);
			
		
		PublicDependencyModuleNames.AddRange(
			new string[]
				{
					"Core", "CoreUObject", "Engine", "InputCore",
				}
			);
			
		
		PrivateDependencyModuleNames.AddRange(
			new string[]
				{
					"UnrealEd",
					"Slate",
					"SlateCore",
					"EditorStyle",
					"GraphEditor",
					"BlueprintGraph",
					"KismetCompiler",
					"DTRedis",
					"ToolMenus",
				}
			);
		
		
		DynamicallyLoadedModuleNames.AddRange(
			new string[]
				{
				}
			);
	}
}
