from telethon.sync import TelegramClient

api_id = 33362645
api_hash = "4742faa877dbff7f1dbbfbafd9f09862"
phone = "+79529255525"

print("Подключаемся...")
client = TelegramClient('session', api_id, api_hash)
client.connect()

if not client.is_user_authorized():
    print(f"Отправляем код на {phone}...")
    client.send_code_request(phone)
    code = input("Введи код из Telegram: ")
    client.sign_in(phone, code)

print("Успешно!")
me = client.get_me()
print(f"Вошли как: {me.first_name}")
client.disconnect()
