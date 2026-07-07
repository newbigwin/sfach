# Shadow Fight 4: Arena Tournament Bot

Бот для управления турнирами по Shadow Fight 4: Arena.

## Установка

1. Получите токен бота у @BotFather в Telegram
2. Вставьте токен в `config.py`
3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Запустите бота:

```bash
python bot.py
```

## Деплой на PythonAnywhere

1. Зарегистрируйтесь на [pythonanywhere.com](https://www.pythonanywhere.com)
2. Откройте консоль Bash
3. Клонируйте проект или загрузите файлы
4. Установите зависимости:

```bash
pip install -r requirements.txt
```

5. Откройте задачи (Tasks) и создайте новую:
   - Тип: Always-running task
   - Команда: `python bot.py`

6. Запустите задачу

## Функции

### Админ-панель (/admin)
- Создание событий
- Создание голосований (3 типа)
- Мут всех участников
- Созыв всех участников
- Удаление событий
- Закрытие голосований

### Участники
- Просмотр событий
- Участие в голосованиях
- Просмотр результатов

## Структура файлов

```
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── database.py         # Работа с БД
├── requirements.txt    # Зависимости
└── handlers/
    ├── admin.py        # Админ-панель
    └── user.py         # Пользовательские команды
```
