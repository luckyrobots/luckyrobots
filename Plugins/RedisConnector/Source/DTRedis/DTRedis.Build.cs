// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

using UnrealBuildTool;

public class DTRedis : ModuleRules
{
	public DTRedis(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		
		// 包含目录中的头文件并公开到外部模块
		PublicIncludePaths.AddRange(new string[] { });
		// 包含目录中的头文件并不公开到外部模块，外部模块访问不到头文件
		PrivateIncludePaths.AddRange(new string[] { });
		PublicDependencyModuleNames.AddRange(
			new string[]
				{
					"Core",
					"CoreUObject",
					"Engine",
					"DTRedisLib",
					"Projects"
				}
			);

		PrivateDependencyModuleNames.AddRange(new string[] { });
		DynamicallyLoadedModuleNames.AddRange(new string[] { });
		bEnableExceptions = true;
	}
}
