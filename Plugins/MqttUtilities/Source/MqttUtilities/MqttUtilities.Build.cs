// Copyright (c) 2023 T4lus Development

using System.IO;
using UnrealBuildTool;

#if UE_5_0_OR_LATER
using EpicGames.Core;
#else
using Tools.DotNETCommon;
#endif

public class MqttUtilities : ModuleRules
{
	public MqttUtilities(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicIncludePaths.AddRange(
			new string[] {
                Path.Combine (ModuleDirectory, "Public")
				// ... add public include paths required here ...
			}
			);


		PrivateIncludePaths.AddRange(
			new string[] {
                Path.Combine (ModuleDirectory, "Private")
				// ... add other private include paths required here ...
			}
			);


		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				// ... add other public dependencies that you statically link with here ...
			}
			);


		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"CoreUObject",
				"Engine",
                "Projects",
                // ... add private dependencies that you statically link with here ...
			}
			);


		DynamicallyLoadedModuleNames.AddRange(
			new string[]
			{
				// ... add any modules that your module loads dynamically here ...
			}
			);


        // Additional routine for Windows
        if (Target.Platform == UnrealTargetPlatform.Win64)
        {
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private/Windows"));

            LoadThirdPartyLibrary("mosquitto", Target);
            LoadThirdPartyLibrary("mosquittopp", Target);
        }

        // Additional routine for Mac
        if (Target.Platform == UnrealTargetPlatform.Mac)
        {
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private/Mac"));

            LoadThirdPartyLibrary("mosquitto", Target);
            LoadThirdPartyLibrary("mosquittopp", Target);
        }

        // Additional routine for iOS
        if (Target.Platform == UnrealTargetPlatform.IOS)
        {
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private/IOS"));

            PublicAdditionalFrameworks.Add(new Framework("MQTTClient", "../ThirdParty/IOS/MQTTClient.embeddedframework.zip"));
			PublicAdditionalFrameworks.Add(new Framework("SocketRocket", "../ThirdParty/IOS/SocketRocket.embeddedframework.zip"));

			PublicAdditionalLibraries.Add("/usr/lib/libicucore.dylib");

            PublicFrameworks.AddRange(
                new string[]
                {
					"Foundation",
					"Security",
                    "CFNetwork",
					"CoreData"
                }
            );

            PrivateDependencyModuleNames.AddRange(new string[] { "Launch" });
            string PluginPath = Utils.MakePathRelativeTo(ModuleDirectory, Target.RelativeEnginePath);

            AdditionalPropertiesForReceipt.Add("IOSPlugin", Path.Combine(PluginPath, "MqttUtilities_IOS_UPL.xml"));
        }

        // Additional routine for Android
        if (Target.Platform == UnrealTargetPlatform.Android)
        {
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private/Android"));

            PrivateDependencyModuleNames.AddRange(new string[] { "Launch" });
            string PluginPath = Utils.MakePathRelativeTo(ModuleDirectory, Target.RelativeEnginePath);

            AdditionalPropertiesForReceipt.Add("AndroidPlugin", Path.Combine(PluginPath, "MqttUtilities_Android_UPL.xml"));
        }

        // Additional routine for Windows
        if (Target.Platform == UnrealTargetPlatform.Linux)
        {
            PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private/Linux"));

            LoadThirdPartyLibrary("libmosquitto", Target);
            LoadThirdPartyLibrary("libmosquittopp", Target);
        }
  	}

    public void LoadThirdPartyLibrary(string libname, ReadOnlyTargetRules Target)
    {
        string StaticLibExtension = ".lib";
        string DynamicLibExtension = string.Empty;

        if(Target.Platform == UnrealTargetPlatform.Win64)
        {
            DynamicLibExtension = ".dll";
        }
        if(Target.Platform == UnrealTargetPlatform.Mac)
        {
            DynamicLibExtension = ".dylib";
        }
        if(Target.Platform == UnrealTargetPlatform.Linux)
        {
            DynamicLibExtension = ".so";
						StaticLibExtension = "_static.a";
        }

        string ThirdPartyPath = Path.Combine(ModuleDirectory, "../ThirdParty", Target.Platform.ToString());
        string LibrariesPath = Path.Combine(ThirdPartyPath, libname, "libraries");
        string IncludesPath = Path.Combine(ThirdPartyPath, libname, "includes");
        string BinariesPath = Path.GetFullPath(Path.Combine(ModuleDirectory, "../../Binaries", Target.Platform.ToString()));

        // Link static library (Windows only)

        if(Target.Platform == UnrealTargetPlatform.Win64 || Target.Platform == UnrealTargetPlatform.Linux)
        {
            PublicAdditionalLibraries.Add(Path.Combine(LibrariesPath, libname + StaticLibExtension));
        }

        // Copy dynamic library to Binaries folder

        if (!Directory.Exists(BinariesPath))
        {
            Directory.CreateDirectory(BinariesPath);
        }

        if (!File.Exists(Path.Combine(BinariesPath, libname + DynamicLibExtension)))
        {
            File.Copy(Path.Combine(LibrariesPath, libname + DynamicLibExtension), Path.Combine(BinariesPath, libname + DynamicLibExtension), true);
        }

        // Set up dynamic library
        if (Target.Platform == UnrealTargetPlatform.Win64)
        {
            PublicDelayLoadDLLs.Add(libname + DynamicLibExtension);
        }
        if (Target.Platform == UnrealTargetPlatform.Mac)
        {
            PublicDelayLoadDLLs.Add(Path.Combine(BinariesPath, libname + DynamicLibExtension));
        }
        if (Target.Platform == UnrealTargetPlatform.Linux)
        {
            PublicDelayLoadDLLs.Add(Path.Combine(BinariesPath, libname + DynamicLibExtension));
        }

        RuntimeDependencies.Add(Path.Combine(BinariesPath, libname + DynamicLibExtension));

        // Set up include path
        PublicIncludePaths.Add(IncludesPath);

        // Add definitions
        PublicDefinitions.Add(string.Format("WITH_" + libname.ToUpper() + "_BINDING={0}", 1));
    }
}
