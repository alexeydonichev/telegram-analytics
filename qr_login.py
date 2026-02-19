from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio
import qrcode
import getpass

API_ID = 35668407
API_HASH = "b18ff2c86b7d4617d39603069cd1b5b0"

async def main():
    client = TelegramClient('session', API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("=" * 40)
        print("Сканируй QR в Telegram!")
        print("Настройки → Устройства → Подключить")
        print("=" * 40)
        print()
        
        qr = await client.qr_login()
        
        qr_code = qrcode.QRCode()
        qr_code.add_data(qr.url)
        qr_code.print_ascii()
        
        print("\nЖду сканирование...")
        
        try:
            await qr.wait(timeout=120)
        except SessionPasswordNeededError:
            print("\n🔐 Нужен пароль 2FA!")
            password = getpass.getpass("Введи пароль: ")
            await client.sign_in(password=password)
        
        print("\n✅ Вход выполнен!")
    
    me = await client.get_me()
    print(f"Привет, {me.first_name}!")
    
    await client.disconnect()

asyncio.run(main())
