import subprocess
import sys

def menu():
    print("\n" + "="*50)
    print("📊 TELEGRAM ANALYTICS SYSTEM")
    print("="*50)
    print("\n1. 📥 Парсить канал/группу/чат")
    print("2. 📊 Показать аналитику")
    print("3. 📤 Экспорт для Claude")
    print("4. 🗄️  Инициализировать базу")
    print("0. ❌ Выход")
    
    choice = input("\nВыбери действие: ").strip()
    
    if choice == "1":
        subprocess.run([sys.executable, "parser.py"])
    elif choice == "2":
        subprocess.run([sys.executable, "analytics.py"])
    elif choice == "3":
        subprocess.run([sys.executable, "export_claude.py"])
    elif choice == "4":
        from database import init_db
        init_db()
    elif choice == "0":
        print("👋 Пока!")
        sys.exit()
    else:
        print("❌ Неверный выбор")
    
    menu()

if __name__ == "__main__":
    menu()
