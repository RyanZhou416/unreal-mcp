#include "UnrealMCPBridge.h"
#include "MCPServerRunnable.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "HAL/RunnableThread.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "JsonObjectConverter.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Async/Async.h"
// Add Blueprint related includes
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
// UE5.5 correct includes
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
// Blueprint Graph specific includes
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "GameFramework/InputSettings.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
// Include our new command handler classes
#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPProjectCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Commands/UnrealMCPUMGCommands.h"
#include "UnrealMCPModule.h"

#define LogTemp LogUnrealMCP

// Default settings
#define MCP_SERVER_HOST "127.0.0.1"
#define MCP_SERVER_PORT 55557

namespace
{
    bool IsCommandSuccessful(const TSharedPtr<FJsonObject>& ResultJson, FString& OutErrorMessage)
    {
        OutErrorMessage.Empty();

        if (!ResultJson.IsValid())
        {
            OutErrorMessage = TEXT("Command returned invalid JSON object");
            return false;
        }

        if (ResultJson->HasTypedField<EJson::String>(TEXT("status")))
        {
            const FString Status = ResultJson->GetStringField(TEXT("status"));
            if (Status.Equals(TEXT("error"), ESearchCase::IgnoreCase))
            {
                OutErrorMessage = ResultJson->GetStringField(TEXT("error"));
                return false;
            }
            return true;
        }

        if (ResultJson->HasTypedField<EJson::Boolean>(TEXT("success")))
        {
            const bool bSuccess = ResultJson->GetBoolField(TEXT("success"));
            if (!bSuccess)
            {
                OutErrorMessage = ResultJson->GetStringField(TEXT("error"));
            }
            return bSuccess;
        }

        if (ResultJson->HasTypedField<EJson::String>(TEXT("error")))
        {
            OutErrorMessage = ResultJson->GetStringField(TEXT("error"));
            return false;
        }

        return true;
    }

    TSharedPtr<FJsonObject> ExtractNormalizedResult(const TSharedPtr<FJsonObject>& ResultJson)
    {
        if (!ResultJson.IsValid())
        {
            return MakeShared<FJsonObject>();
        }

        if (ResultJson->HasTypedField<EJson::Object>(TEXT("result")))
        {
            return ResultJson->GetObjectField(TEXT("result"));
        }

        TSharedPtr<FJsonObject> Normalized = MakeShared<FJsonObject>(*ResultJson);
        Normalized->RemoveField(TEXT("status"));
        Normalized->RemoveField(TEXT("success"));
        Normalized->RemoveField(TEXT("error"));
        return Normalized;
    }
}

UUnrealMCPBridge::UUnrealMCPBridge()
{
    EditorCommands = MakeShared<FUnrealMCPEditorCommands>();
    BlueprintCommands = MakeShared<FUnrealMCPBlueprintCommands>();
    BlueprintNodeCommands = MakeShared<FUnrealMCPBlueprintNodeCommands>();
    ProjectCommands = MakeShared<FUnrealMCPProjectCommands>();
    UMGCommands = MakeShared<FUnrealMCPUMGCommands>();
    BuildCommandRegistry();
}

UUnrealMCPBridge::~UUnrealMCPBridge()
{
    CommandRegistry.Empty();
    EditorCommands.Reset();
    BlueprintCommands.Reset();
    BlueprintNodeCommands.Reset();
    ProjectCommands.Reset();
    UMGCommands.Reset();
}

void UUnrealMCPBridge::RegisterCommand(const FString& CommandType, FCommandHandler Handler)
{
    CommandRegistry.Add(CommandType, MoveTemp(Handler));
}

void UUnrealMCPBridge::BuildCommandRegistry()
{
    CommandRegistry.Empty();

    RegisterCommand(TEXT("ping"), [](const TSharedPtr<FJsonObject>&)
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetStringField(TEXT("message"), TEXT("pong"));
        return Result;
    });

    // Editor commands
    RegisterCommand(TEXT("get_actors_in_level"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("get_actors_in_level"), Params); });
    RegisterCommand(TEXT("find_actors_by_name"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("find_actors_by_name"), Params); });
    RegisterCommand(TEXT("spawn_actor"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("spawn_actor"), Params); });
    RegisterCommand(TEXT("create_actor"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("create_actor"), Params); });
    RegisterCommand(TEXT("delete_actor"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("delete_actor"), Params); });
    RegisterCommand(TEXT("set_actor_transform"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("set_actor_transform"), Params); });
    RegisterCommand(TEXT("get_actor_properties"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("get_actor_properties"), Params); });
    RegisterCommand(TEXT("set_actor_property"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("set_actor_property"), Params); });
    RegisterCommand(TEXT("spawn_blueprint_actor"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("spawn_blueprint_actor"), Params); });
    RegisterCommand(TEXT("focus_viewport"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("focus_viewport"), Params); });
    RegisterCommand(TEXT("take_screenshot"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("take_screenshot"), Params); });
    RegisterCommand(TEXT("get_engine_info"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("get_engine_info"), Params); });
    RegisterCommand(TEXT("delete_asset"), [this](const TSharedPtr<FJsonObject>& Params) { return EditorCommands->HandleCommand(TEXT("delete_asset"), Params); });

    // Blueprint commands
    RegisterCommand(TEXT("create_blueprint"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("create_blueprint"), Params); });
    RegisterCommand(TEXT("add_component_to_blueprint"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("add_component_to_blueprint"), Params); });
    RegisterCommand(TEXT("set_component_property"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("set_component_property"), Params); });
    RegisterCommand(TEXT("set_physics_properties"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("set_physics_properties"), Params); });
    RegisterCommand(TEXT("compile_blueprint"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("compile_blueprint"), Params); });
    RegisterCommand(TEXT("set_blueprint_property"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("set_blueprint_property"), Params); });
    RegisterCommand(TEXT("set_static_mesh_properties"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("set_static_mesh_properties"), Params); });
    RegisterCommand(TEXT("set_pawn_properties"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintCommands->HandleCommand(TEXT("set_pawn_properties"), Params); });

    // Blueprint node commands
    RegisterCommand(TEXT("connect_blueprint_nodes"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("connect_blueprint_nodes"), Params); });
    RegisterCommand(TEXT("add_blueprint_get_self_component_reference"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_get_self_component_reference"), Params); });
    RegisterCommand(TEXT("add_blueprint_self_reference"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_self_reference"), Params); });
    RegisterCommand(TEXT("find_blueprint_nodes"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("find_blueprint_nodes"), Params); });
    RegisterCommand(TEXT("add_blueprint_event_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_event_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_input_action_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_input_action_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_branch_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_branch_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_spawn_actor_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_spawn_actor_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_function_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_function_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_get_component_node"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_get_component_node"), Params); });
    RegisterCommand(TEXT("add_blueprint_variable"), [this](const TSharedPtr<FJsonObject>& Params) { return BlueprintNodeCommands->HandleCommand(TEXT("add_blueprint_variable"), Params); });

    // Project commands
    RegisterCommand(TEXT("create_input_mapping"), [this](const TSharedPtr<FJsonObject>& Params) { return ProjectCommands->HandleCommand(TEXT("create_input_mapping"), Params); });

    // UMG commands
    RegisterCommand(TEXT("create_umg_widget_blueprint"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("create_umg_widget_blueprint"), Params); });
    RegisterCommand(TEXT("add_text_block_to_widget"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("add_text_block_to_widget"), Params); });
    RegisterCommand(TEXT("add_button_to_widget"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("add_button_to_widget"), Params); });
    RegisterCommand(TEXT("bind_widget_event"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("bind_widget_event"), Params); });
    RegisterCommand(TEXT("set_text_block_binding"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("set_text_block_binding"), Params); });
    RegisterCommand(TEXT("add_widget_to_viewport"), [this](const TSharedPtr<FJsonObject>& Params) { return UMGCommands->HandleCommand(TEXT("add_widget_to_viewport"), Params); });
}

// Initialize subsystem
void UUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Initializing"));
    
    bIsRunning = false;
    ListenerSocket = nullptr;
    ConnectionSocket = nullptr;
    ServerThread = nullptr;
    Port = MCP_SERVER_PORT;
    FIPv4Address::Parse(MCP_SERVER_HOST, ServerAddress);

    // Start the server automatically
    StartServer();
}

// Clean up resources when subsystem is destroyed
void UUnrealMCPBridge::Deinitialize()
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Shutting down"));
    StopServer();
}

// Start the MCP server
void UUnrealMCPBridge::StartServer()
{
    if (bIsRunning)
    {
        UE_LOG(LogTemp, Warning, TEXT("UnrealMCPBridge: Server is already running"));
        return;
    }

    // Create socket subsystem
    ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    if (!SocketSubsystem)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to get socket subsystem"));
        return;
    }

    // Create listener socket
    TSharedPtr<FSocket> NewListenerSocket = MakeShareable(SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealMCPListener"), false));
    if (!NewListenerSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create listener socket"));
        return;
    }

    // Allow address reuse for quick restarts
    NewListenerSocket->SetReuseAddr(true);
    NewListenerSocket->SetNonBlocking(true);

    // Bind to address
    FIPv4Endpoint Endpoint(ServerAddress, Port);
    if (!NewListenerSocket->Bind(*Endpoint.ToInternetAddr()))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to bind listener socket to %s:%d"), *ServerAddress.ToString(), Port);
        return;
    }

    // Start listening
    if (!NewListenerSocket->Listen(5))
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to start listening"));
        return;
    }

    ListenerSocket = NewListenerSocket;
    bIsRunning = true;
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server started on %s:%d"), *ServerAddress.ToString(), Port);

    // Start server thread
    ServerThread = FRunnableThread::Create(
        new FMCPServerRunnable(this, ListenerSocket),
        TEXT("UnrealMCPServerThread"),
        0, TPri_Normal
    );

    if (!ServerThread)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealMCPBridge: Failed to create server thread"));
        StopServer();
        return;
    }
}

// Stop the MCP server
void UUnrealMCPBridge::StopServer()
{
    if (!bIsRunning)
    {
        return;
    }

    bIsRunning = false;

    // Clean up thread
    if (ServerThread)
    {
        ServerThread->Kill(true);
        delete ServerThread;
        ServerThread = nullptr;
    }

    // Close sockets
    if (ConnectionSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ConnectionSocket.Get());
        ConnectionSocket.Reset();
    }

    if (ListenerSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenerSocket.Get());
        ListenerSocket.Reset();
    }

    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Server stopped"));
}

// Execute a command received from a client
FString UUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Executing command: %s"), *CommandType);
    
    // Create a promise to wait for the result
    TPromise<FString> Promise;
    TFuture<FString> Future = Promise.GetFuture();
    
    // Queue execution on Game Thread
    AsyncTask(ENamedThreads::GameThread, [this, CommandType, Params, Promise = MoveTemp(Promise)]() mutable
    {
        TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);
        
        try
        {
            const FCommandHandler* Handler = CommandRegistry.Find(CommandType);
            if (Handler == nullptr)
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));

                FString ResultString;
                TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                Promise.SetValue(ResultString);
                return;
            }

            TSharedPtr<FJsonObject> ResultJson = (*Handler)(Params);
            if (!ResultJson.IsValid())
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Command returned invalid result: %s"), *CommandType));

                FString ResultString;
                TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                Promise.SetValue(ResultString);
                return;
            }
            
            FString ErrorMessage;

            if (IsCommandSuccessful(ResultJson, ErrorMessage))
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("success"));
                ResponseJson->SetObjectField(TEXT("result"), ExtractNormalizedResult(ResultJson));
            }
            else
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), ErrorMessage);
            }
        }
        catch (const std::exception& e)
        {
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), UTF8_TO_TCHAR(e.what()));
        }
        
        FString ResultString;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
        FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
        Promise.SetValue(ResultString);
    });
    
    return Future.Get();
}