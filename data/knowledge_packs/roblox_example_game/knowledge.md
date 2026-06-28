# Coin Collector — Complete Roblox (Luau) Example

A minimal but complete game to pattern-match: touch coins to earn points (leaderstats),
persist with DataStore, and buy a server-validated speed boost via a RemoteEvent.

**`ReplicatedStorage/BuySpeed`** — a `RemoteEvent` instance (create it in Studio, no code).

**`ServerScriptService/CoinSystem`** (Script)
```lua
-- Handles leaderstats, DataStore persistence, and safe coin pickups.
local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local coinStore = DataStoreService:GetDataStore("CoinData_v1")

local COIN_VALUE = 5
local touchDebounce = {} -- [player] = true while on cooldown

local function onPlayerAdded(player)
	-- Build leaderstats before parenting so it replicates complete.
	local stats = Instance.new("Folder")
	stats.Name = "leaderstats"

	local coins = Instance.new("IntValue")
	coins.Name = "Coins"
	coins.Value = 0
	coins.Parent = stats
	stats.Parent = player

	-- Load saved value (wrapped: DataStore calls can error).
	local ok, saved = pcall(function()
		return coinStore:GetAsync("Player_" .. player.UserId)
	end)
	if ok and typeof(saved) == "number" then
		coins.Value = saved
	end
end

local function savePlayer(player)
	local stats = player:FindFirstChild("leaderstats")
	if not stats then return end
	local coins = stats:FindFirstChild("Coins")
	if not coins then return end
	pcall(function()
		coinStore:SetAsync("Player_" .. player.UserId, coins.Value)
	end)
end

-- Award coins on touch, with all three safety checks.
local function onCoinTouched(part, hit)
	local character = hit.Parent
	if not character then return end
	if not character:FindFirstChildOfClass("Humanoid") then return end -- a real character
	local player = Players:GetPlayerFromCharacter(character)        -- and a real player
	if not player then return end
	if touchDebounce[player] then return end                       -- per-player cooldown
	touchDebounce[player] = true

	local coins = player.leaderstats.Coins
	coins.Value = coins.Value + COIN_VALUE

	task.wait(0.5)
	touchDebounce[player] = nil
end

-- Connect every part named "Coin" in the world.
for _, part in ipairs(workspace:GetDescendants()) do
	if part:IsA("BasePart") and part.Name == "Coin" then
		part.Touched:Connect(function(hit)
			onCoinTouched(part, hit)
		end)
	end
end

Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(function(player)
	touchDebounce[player] = nil
	savePlayer(player)
end)

-- Flush all data when the server shuts down.
game:BindToClose(function()
	for _, player in ipairs(Players:GetPlayers()) do
		savePlayer(player)
	end
	task.wait(2) -- give SetAsync calls time in Studio
end)
```

**`ServerScriptService/Shop`** (Script)
```lua
-- Server-authoritative shop: validates funds, deducts, applies speed.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local BuySpeed = ReplicatedStorage:WaitForChild("BuySpeed")

local COST = 25
local BOOSTED_SPEED = 32

BuySpeed.OnServerEvent:Connect(function(player)
	-- Never trust the client: re-check everything on the server.
	local stats = player:FindFirstChild("leaderstats")
	if not stats then return end
	local coins = stats:FindFirstChild("Coins")
	if not coins or coins.Value < COST then return end -- can't afford

	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid then return end

	coins.Value = coins.Value - COST       -- deduct first
	humanoid.WalkSpeed = BOOSTED_SPEED      -- then apply
end)
```

**`StarterPlayer/StarterPlayerScripts/ShopClient`** (LocalScript)
```lua
-- Client just sends the request; the server decides if it's allowed.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local BuySpeed = ReplicatedStorage:WaitForChild("BuySpeed")

-- Press E to attempt the purchase.
UserInputService.InputBegan:Connect(function(input, processed)
	if processed then return end
	if input.KeyCode == Enum.KeyCode.E then
		BuySpeed:FireServer()
	end
end)
```

All currency math and validation live on the SERVER; the client never sets WalkSpeed or Coins. Coins are any `BasePart` named `Coin` in `workspace`.
