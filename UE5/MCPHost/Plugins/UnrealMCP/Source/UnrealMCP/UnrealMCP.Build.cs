// Copyright Epic Games, Inc. All Rights Reserved.

using System;
using System.IO;
using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
	public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		// ── Read engine version ────────────────────────────────────────
		int EngineMajor = 5, EngineMinor = 5;
		BuildVersion OutVersion;
		if (BuildVersion.TryRead(BuildVersion.GetDefaultFileName(), out OutVersion))
		{
			EngineMajor = OutVersion.MajorVersion;
			EngineMinor = OutVersion.MinorVersion;
		}
		bool bIsUE55OrLater = (EngineMajor > 5) || (EngineMajor == 5 && EngineMinor >= 5);
		bool bIsUE54OrLater = (EngineMajor > 5) || (EngineMajor == 5 && EngineMinor >= 4);

		// ── Plugin version ─────────────────────────────────────────────
		// Keep in sync with UnrealMCP.uplugin VersionName
		PublicDefinitions.Add("UNREALMCP_PLUGIN_VERSION=\"1.0\"");

		// ── Adaptive IWYU ──────────────────────────────────────────────
		// UE 5.5+ replaced bEnforceIWYU with the IWYUSupport enum.
		// We use reflection so this Build.cs compiles on any UE 5.x.
		var iwyu = GetType().GetProperty("IWYUSupport");
		if (iwyu != null)
		{
			var fullValue = Enum.Parse(iwyu.PropertyType, "Full");
			iwyu.SetValue(this, fullValue);
		}
		else
		{
			var enforce = GetType().GetProperty("bEnforceIWYU");
			if (enforce != null) enforce.SetValue(this, true);
		}

		// ── Dependencies ───────────────────────────────────────────────
		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"InputCore",
				"Networking",
				"Sockets",
				"HTTP",
				"Json",
				"JsonUtilities",
				"DeveloperSettings"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"UnrealEd",
				"EditorScriptingUtilities",
				"EditorSubsystem",
				"Slate",
				"SlateCore",
				"UMG",
				"Kismet",
				"KismetCompiler",
				"BlueprintGraph",
				"Projects",
				"AssetRegistry"
			}
		);

		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(
				new string[]
				{
					"PropertyEditor",
					"ToolMenus",
					"UMGEditor",
				}
			);

			// BlueprintEditorLibrary was introduced in UE 5.5
			if (bIsUE55OrLater)
			{
				PrivateDependencyModuleNames.Add("BlueprintEditorLibrary");
				PublicDefinitions.Add("WITH_BLUEPRINT_EDITOR_LIBRARY=1");
			}
			else
			{
				PublicDefinitions.Add("WITH_BLUEPRINT_EDITOR_LIBRARY=0");
			}
		}
	}
}
