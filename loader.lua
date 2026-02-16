--[[ ZUEV HUB - ЗАГРУЗЧИК ]]--
repeat task.wait() until game:IsLoaded()

-- Проверяем, ввел ли пользователь ключ
if not script_key then
    game.Players.LocalPlayer:Kick("Используй: script_key='ZV-XXXXXX'; loadstring(...)")
    return
end

-- Функция получения HWID
local function getHWID()
    local success, hwid = pcall(function()
        return game:GetService("RbxAnalyticsService"):GetClientId()
    end)
    return (success and hwid) or "HWID_" .. game.Players.LocalPlayer.UserId
end

-- Функция проверки ключа на твоем сервере
local function verifyKey(key, hwid)
    local url = "https://zuevv.onrender.com/verify"
    local data = game:GetService("HttpService"):JSONEncode({key = key, hwid = hwid})
    
    local success, response = pcall(function()
        return game:GetService("HttpService"):PostAsync(url, data, Enum.HttpContentType.ApplicationJson)
    end)
    
    if success then
        return game:GetService("HttpService"):JSONDecode(response)
    else
        return {status = "error", message = "Connection failed"}
    end
end

-- Запускаем проверку
local result = verifyKey(script_key, getHWID())

if result.status == "success" then
    -- Загружаем основной скрипт
    loadstring(game:HttpGet("https://raw.githubusercontent.com/NikitosZuev/Zuevv/main/main.lua"))()
else
    game.Players.LocalPlayer:Kick("Ошибка: " .. (result.message or "Неверный ключ"))
end
