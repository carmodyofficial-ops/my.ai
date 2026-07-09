# Unreal Engine 5 Reference

## Core Framework — Actors, Components, Gameplay Classes
- `UObject` = base of reflected types (GC-managed, serializable). `AActor` = anything placeable in a level (has `Transform`, can be spawned). `UActorComponent` = reusable behavior attached to an Actor; `USceneComponent` adds a transform (attach hierarchy); `UPrimitiveComponent` adds rendering/collision (`UStaticMeshComponent`, `USkeletalMeshComponent`).
- One Actor has one **root component**; others attach beneath it (`SetupAttachment(RootComponent)` in constructor; `AttachToComponent` at runtime).
- Gameplay framework (per player/match):
  - `AGameModeBase` / `AGameMode` — rules, spawning; **server-only**, does not exist on clients.
  - `AGameStateBase` — replicated match state (score, phase) — exists everywhere.
  - `APlayerState` — per-player replicated data (name, score).
  - `APawn` / `ACharacter` — the physical avatar; `ACharacter` adds `UCharacterMovementComponent` + capsule + mesh.
  - `AController` (`APlayerController` / `AAIController`) — the "brain" that possesses a Pawn (`Possess`/`UnPossess`). Input & camera live on PlayerController; survives Pawn death.
  - `UGameInstance` — persists across level loads (save data, sessions). Single instance per game.
- Spawn: `GetWorld()->SpawnActor<AMyActor>(Class, Location, Rotation, Params)`. Destroy: `Actor->Destroy()` (marks pending kill; GC reclaims). Never `delete` a UObject.
- Access: `GetWorld()`, `GetGameInstance()`, `UGameplayStatics::GetPlayerController(this,0)`, `GetActorLocation/SetActorLocation`.

## Blueprints vs C++
- **Reflection** drives the editor/BP/serialization/replication. Expose members with macros:
  - `UCLASS(Blueprintable)` / `USTRUCT(BlueprintType)` / `UENUM(BlueprintType)`.
  - `UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="X")` — editable in Inspector + BP graph. Specifiers: `EditDefaultsOnly` (class defaults, not instance), `VisibleAnywhere`, `Replicated`, `Transient`, `meta=(ClampMin="0")`.
  - `UFUNCTION(BlueprintCallable)` — callable from BP; `BlueprintPure` (no exec pins, side-effect-free); `BlueprintImplementableEvent` (defined in BP); `BlueprintNativeEvent` (C++ default `_Implementation` + BP override); `Server`/`Client`/`NetMulticast` for RPCs.
- **UPROPERTY is required for GC**: a raw `UObject*` member without `UPROPERTY()` will NOT be tracked and can be garbage-collected out from under you (dangling pointer). Always mark UObject pointers `UPROPERTY()` or use `TWeakObjectPtr`.
- Containers: `TArray<T>`, `TMap<K,V>`, `TSet<T>` (not std). Strings: `FString` (mutable), `FName` (interned, fast compare, asset/socket IDs), `FText` (localized UI). Convert deliberately.
- BP inherits from C++: put perf-critical/base logic in C++, expose tunables + designer glue to BP. Nativize is deprecated in UE5.

## Tick vs Events
- `Tick(DeltaSeconds)` runs every frame — **expensive at scale**. Disable when idle: `PrimaryActorTick.bCanEverTick=false`, or `SetActorTickEnabled(false)`, or throttle `PrimaryActorTick.TickInterval=0.1f`.
- Prefer **event-driven**: `Timers` (`GetWorldTimerManager().SetTimer(Handle,this,&AX::Fn,Rate,bLoop)`), delegates/events, overlap callbacks (`OnComponentBeginOverlap`), `Timelines` (BP), latent actions.
- Multiply per-frame motion by `DeltaSeconds`. Tick order is not guaranteed unless you set tick dependencies (`AddTickPrerequisiteActor`).

## Rendering — Nanite, Lumen, Materials
- **Nanite**: virtualized micro-polygon geometry; renders film-quality static meshes without manual LODs. Enable per-mesh. Caveats: opaque/masked only (limited translucency/masked support historically), no skeletal meshes (WPO/deformation limited), draws via visibility buffer not classic draw calls.
- **Lumen**: real-time GI + reflections (software ray tracing by default; hardware RT optional). Replaces baked lightmaps for dynamic scenes; costs GPU. Alternatives: baked lighting (Lightmass) for static/mobile.
- **Materials**: node graph compiled to shaders. Shading models: Default Lit (PBR: Base Color, Metallic, Roughness, Specular, Normal). **Material Instances** (`UMaterialInstanceDynamic` at runtime via `CreateDynamicMaterialInstance`; `UMaterialInstanceConstant` in editor) expose parameters WITHOUT recompiling — always parameterize instead of duplicating base materials.
- `UMeshComponent::SetMaterial(index, mat)`. Set params: `MID->SetScalarParameterValue("Emissive", v)`.

## Physics — Chaos
- Chaos is the physics engine (replaced PhysX). `SetSimulatePhysics(true)` on a primitive component makes it dynamic; drive with `AddForce`, `AddImpulse`, `SetPhysicsLinearVelocity` — not `SetActorLocation` (fights the solver / teleports through collision).
- Collision setup: **Collision Presets** + Object Channels + Response (Block/Overlap/Ignore). Overlap events need "Generate Overlap Events" checked on both. Trace channels for line traces.
- `LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params)`; `FCollisionQueryParams` to ignore self.
- `UCharacterMovementComponent` is kinematic-ish (not raw rigid body): tune `MaxWalkSpeed`, `JumpZVelocity`, `GravityScale`, movement modes.

## Replication / Networking
- Model: **server-authoritative**. Server owns truth; clients predict/receive. Listen server = host is also a client; dedicated server = headless.
- Replicate a property: `UPROPERTY(Replicated)` + declare in `GetLifetimeReplicatedProps(...)` via `DOREPLIFETIME(AX, Prop)`. `ReplicatedUsing=OnRep_Fn` fires a callback on clients when value changes (`UPROPERTY(ReplicatedUsing=OnRep_Health)`).
- Set `bReplicates=true` (Actor) and `SetIsReplicated(true)` (component) and `bReplicateMovement` for transform.
- **RPCs**: `UFUNCTION(Server, Reliable, WithValidation)` (client→server), `Client` (server→owning client), `NetMulticast` (server→all). Reliable vs Unreliable (movement = unreliable/frequent). Validate server RPCs.
- Authority check: `HasAuthority()` / `GetLocalRole()==ROLE_Authority`. Run gameplay logic on server, cosmetic on all.
- Relevancy & `NetCullDistanceSquared`, `NetUpdateFrequency` control bandwidth.

## Asset Pipeline
- Content = `.uasset`/`.umap` (binary). **Reference by soft/hard**: hard ref loads dependency immediately; `TSoftObjectPtr`/`TSoftClassPtr` = async load on demand (avoids pulling whole trees into memory). Use `UAssetManager` / `StreamableManager` for async loads.
- Import: FBX/glTF meshes, textures (power-of-two, sRGB for color / linear for normals-roughness). Level streaming + **World Partition** (UE5) auto-streams large open worlds by grid cells.
- Cooking = build assets per-platform for packaged builds; editor uses uncooked.

## Modules, Delegates, Subsystems, UI
- Project = C++ **modules** (`.Build.cs` lists dependencies like `Core`, `CoreUObject`, `Engine`, `EnhancedInput`). Add public deps there or you get link errors.
- **Delegates** = type-safe callbacks for events: `DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDied, int32, Cause)`; a `UPROPERTY(BlueprintAssignable)` dynamic multicast delegate is bindable in Blueprints. Bind with `AddDynamic`, broadcast with `.Broadcast(...)`.
- **Subsystems** = managed singletons with automatic lifetime, replacing manual singletons: `UGameInstanceSubsystem`, `UWorldSubsystem`, `ULocalPlayerSubsystem`. `GetGameInstance()->GetSubsystem<UMySubsystem>()`.
- **Enhanced Input** (UE5 default): `UInputAction` assets + `UInputMappingContext` bound in the PlayerController/Pawn; bind via `UEnhancedInputComponent::BindAction(Action, ETriggerEvent::Triggered, this, &AX::Fn)`.
- **UMG** = UI (`UUserWidget` in C++, designed in the Widget Blueprint). Create with `CreateWidget<UMyWidget>(PC, Class)`, `AddToViewport()`. Slate is the underlying C++ UI framework.
- **GAS** (Gameplay Ability System) = optional plugin for abilities/attributes/effects/cooldowns, replication-aware — standard for complex RPG/action combat.

## Gotchas -> Fix
- **Raw `UObject*` gets GC'd (crash/dangling)** -> mark it `UPROPERTY()`, or use `TWeakObjectPtr`/`TStrongObjectPtr`; check `IsValid(Ptr)` before use.
- **Every Actor ticking = frame-rate collapse** -> `bCanEverTick=false` by default; use timers/events; set `TickInterval` for slow logic.
- **Blueprint hot-path is slow (VM interpreted)** -> move per-frame math/loops to C++; keep BP for glue/events; avoid heavy per-node logic in Event Tick.
- **`GameMode` is null on clients** -> it's server-only; put shared replicated state in `GameState`/`PlayerState`, not GameMode.
- **Replicated var didn't update on client** -> forgot `DOREPLIFETIME` in `GetLifetimeReplicatedProps`, or `bReplicates=false`, or you set it on the client (only server-set replicates).
- **Cast failures / null after level load** -> `Cast<T>()` returns null on mismatch — always null-check; cross-level refs die, use `GameInstance` or SaveGame to persist.
- **`SetActorLocation` on a physics body tunnels/jitters** -> use `AddImpulse`/`SetPhysicsLinearVelocity`; use `SetActorLocation` only on non-simulating actors, with `bSweep` for collision.
- **Overlap events never fire** -> enable "Generate Overlap Events" on BOTH components and set collision responses to Overlap (not Block/Ignore).
- **Live Coding / hot reload corrupts state or crashes** -> Live Coding handles function bodies; for header/UPROPERTY changes close the editor and full-rebuild; blueprint-derived-from-changed-C++ can invalidate.
- **`FName`/`FString`/`FText` misuse** -> `FName` for IDs (case-insensitive, interned), `FString` for manipulation, `FText` for anything shown to players (localization).
- **Editor crash on Play from uninitialized component** -> create components in the constructor (`CreateDefaultSubobject<UX>(TEXT("Name"))`), not in `BeginPlay`.
- **Async soft-ref used before loaded** -> `TSoftObjectPtr` is null until you request the load; resolve via `StreamableManager.RequestAsyncLoad` and use in the completion callback.
- **Casting to a Blueprint class in C++** -> you generally can't `Cast<>` to a pure-BP type from C++; reference a `TSubclassOf<AParentCppClass>` and set the BP in the editor.
