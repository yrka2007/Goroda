import PyQt5, PyQt6, PySide6
import sys
import json
import random
import re
import unicodedata
import string
import logging
from pathlib import Path
import os
from collections import defaultdict, deque
import time

log_dir = Path("logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "game.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

RUSSIAN_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
FORBIDDEN_CHARS = string.digits + string.punctuation


def norm_city_name(name: str) -> str:
    name = name.lower().replace('ё', 'е')
    name = unicodedata.normalize('NFC', name)
    name = re.sub(r'[^а-я]', '', name)
    return name


def first(norm_name: str) -> str:
    return norm_name[0] if norm_name else ''


def last(norm_name: str) -> str:
    if not norm_name:
        return ''
    # последний символ
    if norm_name[-1] in ('ь', 'ъ', 'ы') and len(norm_name) > 1:
        return norm_name[-2]
    return norm_name[-1]


# Загрузка городов из JSON
def load(json_path: str):
    json_path = Path(json_path)
    if not json_path.exists():
        sample_cities = [
            "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
            "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону",
            "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград", "Краснодар",
            "Саратов", "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Ульяновск",
            "Иркутск", "Хабаровск", "Ярославль", "Владивосток", "Махачкала",
            "Томск", "Оренбург", "Кемерово", "Новокузнецк", "Рязань", "Астрахань",
            "Набережные Челны", "Пенза", "Липецк", "Киров", "Чебоксары", "Тула",
            "Калининград", "Курск", "Сочи", "Улан-Удэ", "Тверь", "Магнитогорск",
            "Иваново", "Брянск", "Белгород", "Сургут", "Владимир"
        ]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(sample_cities, f, ensure_ascii=False, indent=2)
        logging.info(f"Создан файл с городами: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_cities = json.load(f)

    cities1 = {}
    letter_map1 = defaultdict(list)

    for original in raw_cities:
        norm = norm_city_name(original)
        if not norm:
            continue
        if norm in cities1:
            continue
        cities1[norm] = original
        first_letter = first(norm)
        letter_map1[first_letter].append(norm)

    logging.info(f"Загружено {len(cities1)} уникальных городов.")
    return cities1, letter_map1


# игровая логика
def game(cities1, letter_map1):
    used = set()
    available = {letter: list(names) for letter, names in letter_map1.items()}

    first_city_norm = random.choice(list(cities1.keys()))
    first_city_orig = cities1[first_city_norm]

    used.add(first_city_norm)
    first_letter = first(first_city_norm)
    if first_letter in available and first_city_norm in available[first_letter]:
        available[first_letter].remove(first_city_norm)

    print(f"Компьютер начинает: {first_city_orig}")
    logging.info(f"Компьютер: {first_city_orig} (норм: {first_city_norm})")

    current_letter = last(first_city_norm)
    print(f"Вам на букву: {current_letter.upper()}")

    last_moves = deque(maxlen=5)
    last_moves.append(("Компьютер", first_city_orig, current_letter))

    # Счётчики времени для будущих очков
    turn_times = []          # список времени, затраченного на каждый ход игрока
    total_player_time = 0    # суммарное время всех ходов игрока
    turn_number = 0          # номер хода игрока (для информации)

    while True:
        # Ход игрока
        print("\n--- Ваш ход ---")
        start_time = time.time()   # запускаем таймер перед вводом

        while True:
            user_input = input("Ваш город (или 'сдаюсь', 'стоп', 'exit', 'quit' для выхода): ").strip()
            if user_input.lower() in ('сдаюсь', 'стоп', 'exit', 'quit'):
                print("Вы сдались. Игра окончена.")
                logging.info("Игрок сдался.")
                sys.exit(0)

            if any(d in user_input for d in string.digits):
                print("Название города не должно содержать цифр. Попробуйте снова.")
                continue

            norm_user = norm_city_name(user_input)
            if not norm_user:
                print("Некорректное название (после нормализации пусто). Попробуйте снова.")
                continue

            if norm_user not in cities1:
                print("Такого города нет в списке. Попробуйте другой.")
                logging.info(f"Игрок ввёл несуществующий город: {user_input}")
                continue

            if norm_user in used:
                print("Этот город уже был. Выберите другой.")
                continue

            if first(norm_user) != current_letter:
                print(f"Город должен начинаться на букву '{current_letter.upper()}'. Попробуйте снова.")
                continue

            # Ввод корректен – выходим из цикла
            break

        # Фиксируем время, затраченное на ввод
        end_time = time.time()
        turn_time = end_time - start_time
        turn_times.append(turn_time)
        total_player_time += turn_time
        turn_number += 1

        print(f"Время на этот ход: {turn_time:.2f} секунд")

        user_original = cities1[norm_user]
        used.add(norm_user)
        fl = first(norm_user)
        if fl in available and norm_user in available[fl]:
            available[fl].remove(norm_user)

        print(f"Вы назвали: {user_original}")
        logging.info(f"Игрок: {user_original} (норм: {norm_user}) (время: {turn_time:.2f} сек)")
        last_moves.append(("Игрок", user_original, current_letter))

        current_letter = last(norm_user)
        print(f"Компьютер думает... (нужна буква: {current_letter.upper()})")

        # Ход компьютера
        possible = available.get(current_letter, [])
        possible = [c for c in possible if c not in used]

        if not possible:
            print("Компьютер не может найти подходящий город. Вы победили!")
            logging.info("Компьютер проиграл. Игрок победил.")
            break

        comp_norm = random.choice(possible)
        comp_orig = cities1[comp_norm]
        used.add(comp_norm)
        fl = first(comp_norm)
        if fl in available and comp_norm in available[fl]:
            available[fl].remove(comp_norm)

        print(f"Компьютер отвечает: {comp_orig}")
        logging.info(f"Компьютер: {comp_orig} (норм: {comp_norm})")
        last_moves.append(("Компьютер", comp_orig, current_letter))

        current_letter = last(comp_norm)
        print(f"Вам на букву: {current_letter.upper()}")

    # После завершения игры выводим статистику по времени
    if turn_times:
        avg_time = total_player_time / len(turn_times)
        print("\n--- Статистика времени игрока ---")
        print(f"Всего ходов игрока: {turn_number}")
        print(f"Суммарное время: {total_player_time:.2f} секунд")
        print(f"Среднее время на ход: {avg_time:.2f} секунд")
        logging.info(f"Статистика: ходов={turn_number}, сумма={total_player_time:.2f}, среднее={avg_time:.2f}")
    else:
        print("Игрок не сделал ни одного хода.")


if __name__ == "__main__":
    cities_file = Path("cities.json")
    if not os.path.exists(cities_file):
        print("Создан файл из примера")

    cities1, letter_map1 = load(cities_file)
    if not cities1:
        print("Список городов пуст. Игра невозможна.")
        sys.exit(1)

    random.seed()

    try:
        game(cities1, letter_map1)
    except KeyboardInterrupt:
        print("\nИгра прервана пользователем.")
        logging.info("Игра прервана по Ctrl+C")
        sys.exit(0)