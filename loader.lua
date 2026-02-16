--[[ ZUEV HUB - ЗАГРУЗЧИК ]]--
repeat task.wait() until game:IsLoaded()

if not script_key then
    game.Players.LocalPlayer:Kick("Используй: script_key='ZV-XXXXXX'; loadstring(...)")
    return
end

local function getHWID()
    local s, h = pcall(game.GetService, game, "RbxAnalyticsService", "GetClientId")
    return (s and h) or "HWID_" .. game.Players.LocalPlayer.UserId
end

local function verifyKey(key, hwid)
    local url = "https://zuevv.onrender.com/verify"
    local data = game:GetService("HttpService"):JSONEncode({key = key, hwid = hwid})
    
    -- Пробуем до 3 раз с интервалом 10 секунд
    for attempt = 1, 3 do
        local success, response = pcall(function()
            return game:GetService("HttpService"):PostAsync(
                url, 
                data, 
                Enum.HttpContentType.ApplicationJson, 
                false, 
                nil, 
                30  -- таймаут 30 сек
            )
        end)
        
        if success then
            return game:GetService("HttpService"):JSONDecode(response)
        else
            if attempt < 3 then
                print("⚠️ Сервер просыпается, попытка " .. attempt + 1 .. "/3 через 10 сек...")
                task.wait(10)
            end
        end
    end
    
    return {status = "error", message = "Сервер не отвечает. Попробуй через минуту."}
end

local result = verifyKey(script_key, getHWID())

if result.status == "success" then
    loadstring(game:HttpGet("https://raw.githubusercontent.com/NikitosZuev/Zuevv/main/main.lua"))()
else
    game.Players.LocalPlayer:Kick("Ошибка: " .. (result.message or "Неверный ключ"))
end
