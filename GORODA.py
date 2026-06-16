import sys
import json
import random
import re
import unicodedata
import string
import time
import os
from pathlib import Path
from collections import defaultdict, deque

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QMessageBox, QListWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# ---------- Константы и утилиты ----------
RUSSIAN_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
FORBIDDEN_CHARS = string.digits + string.punctuation
BASE_SCORE = 100
MAX_TIME = 60
SUPER_TIME_LIMIT = 30


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
    if norm_name[-1] in ('ь', 'ъ', 'ы') and len(norm_name) > 1:
        return norm_name[-2]
    return norm_name[-1]


def calculate_score(turn_time: float) -> int:
    time_for_score = min(turn_time, MAX_TIME)
    score = BASE_SCORE / (time_for_score + 1)
    return int(score)


def load_cities(json_path: str):
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

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_cities = json.load(f)

    cities_dict = {}
    letter_map = defaultdict(list)

    for original in raw_cities:
        norm = norm_city_name(original)
        if not norm:
            continue
        if norm in cities_dict:
            continue
        cities_dict[norm] = original
        first_letter = first(norm)
        letter_map[first_letter].append(norm)

    return cities_dict, letter_map


def get_writable_path(filename):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


# ---------- Логика игры ----------
class GameLogic:
    def __init__(self, cities_file):
        self.cities, self.letter_map = load_cities(cities_file)
        self.reset_state()

    def reset_state(self):
        self.used = set()
        available = {letter: list(names) for letter, names in self.letter_map.items()}
        self.available = available
        self.current_letter = None
        self.last_moves = deque(maxlen=10)
        self.total_score = 0
        self.turn_number = 0
        self.game_over = False
        self.mode = None
        self.repeat_occurred = False

    def start(self, mode):
        self.reset_state()
        self.mode = mode  # Устанавливаем mode ПОСЛЕ reset_state()
        if not self.cities:
            return None, None
        first_norm = random.choice(list(self.cities.keys()))
        first_orig = self.cities[first_norm]
        self.used.add(first_norm)
        first_letter = first(first_norm)
        if first_letter in self.available and first_norm in self.available[first_letter]:
            self.available[first_letter].remove(first_norm)
        self.current_letter = last(first_norm)
        self.last_moves.append(("Компьютер", first_orig, self.current_letter))
        return first_orig, self.current_letter

    def process_player_city(self, city_input, turn_time):
        norm = norm_city_name(city_input)
        if not norm:
            return False, "Некорректное название города.", 0

        if norm not in self.cities:
            return False, "Такого города нет в списке.", 0

        if norm in self.used:
            if self.mode == 'super':
                self.repeat_occurred = True
                return False, "Этот город уже был использован. Повтор запрещён в режиме «Супер-города».", 0
            else:
                return False, "Этот город уже был использован.", 0

        if first(norm) != self.current_letter:
            return False, f"Город должен начинаться на букву '{self.current_letter.upper()}'.", 0

        score = calculate_score(turn_time)
        self.total_score += score
        self.turn_number += 1
        user_original = self.cities[norm]
        self.used.add(norm)
        fl = first(norm)
        if fl in self.available and norm in self.available[fl]:
            self.available[fl].remove(norm)

        self.current_letter = last(norm)
        self.last_moves.append(("Игрок", user_original, self.current_letter))
        return True, "", score

    def computer_move(self):
        possible = self.available.get(self.current_letter, [])
        possible = [c for c in possible if c not in self.used]
        if not possible:
            self.game_over = True
            return None, False
        comp_norm = random.choice(possible)
        comp_orig = self.cities[comp_norm]
        self.used.add(comp_norm)
        fl = first(comp_norm)
        if fl in self.available and comp_norm in self.available[fl]:
            self.available[fl].remove(comp_norm)
        self.current_letter = last(comp_norm)
        self.last_moves.append(("Компьютер", comp_orig, self.current_letter))
        return comp_orig, True

    def save_rating(self, mode):
        rating_file = get_writable_path("rating.json")
        rating_data = []
        if os.path.exists(rating_file):
            with open(rating_file, 'r', encoding='utf-8') as f:
                rating_data = json.load(f)
        entry = {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "score": self.total_score,
            "mode": mode
        }
        rating_data.append(entry)
        rating_data.sort(key=lambda x: x["score"], reverse=True)
        with open(rating_file, 'w', encoding='utf-8') as f:
            json.dump(rating_data, f, ensure_ascii=False, indent=2)


# ---------- Окна GUI ----------
class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Игра «Города»")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Игра «Города»")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_classic = QPushButton("Классический режим")
        btn_super = QPushButton("Режим «Супер-города»")
        btn_rating = QPushButton("Рейтинг")
        btn_exit = QPushButton("Выход")

        for btn in (btn_classic, btn_super, btn_rating, btn_exit):
            btn.setMinimumHeight(40)
            layout.addWidget(btn)

        btn_classic.clicked.connect(lambda: self.start_game('classic'))
        btn_super.clicked.connect(lambda: self.start_game('super'))
        btn_rating.clicked.connect(self.show_rating)
        btn_exit.clicked.connect(self.close)

        layout.addStretch()

    def start_game(self, mode):
        game_dialog = GameDialog(mode, self)
        game_dialog.exec_()

    def show_rating(self):
        rating_dialog = RatingDialog(self)
        rating_dialog.exec_()

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #b0b0b0;
            }
        """)


class GameDialog(QDialog):
    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.logic = GameLogic('cities.json')
        self.player_start_time = None
        self.remaining_time = 0
        self.elapsed_time = 0
        self.is_finished = False

        self.super_timer = QTimer(self)
        self.super_timer.timeout.connect(self.update_super_timer)

        self.classic_timer = QTimer(self)
        self.classic_timer.timeout.connect(self.update_classic_timer)

        self.setWindowTitle("Игра «Города»" if mode == 'classic' else "Супер-города")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.start_new_game()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()

        self.label_time = QLabel()
        self.label_time.setFont(QFont("Arial", 16, QFont.Bold))
        self.label_time.setAlignment(Qt.AlignCenter)
        self.label_time.setMinimumWidth(200)

        self.label_score = QLabel("Очки: 0")
        self.label_score.setFont(QFont("Arial", 14))

        top_layout.addWidget(self.label_time)
        top_layout.addWidget(self.label_score)
        top_layout.addStretch()

        btn_rules = QPushButton("Правила")
        btn_rules.clicked.connect(self.show_rules)
        top_layout.addWidget(btn_rules)
        layout.addLayout(top_layout)

        self.label_round = QLabel()
        self.label_round.setFont(QFont("Arial", 14))
        self.label_round.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_round)

        input_layout = QHBoxLayout()
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Введите город")
        self.line_edit.returnPressed.connect(self.submit_city)
        self.btn_submit = QPushButton("Ответить")
        self.btn_submit.clicked.connect(self.submit_city)
        input_layout.addWidget(self.line_edit)
        input_layout.addWidget(self.btn_submit)
        layout.addLayout(input_layout)

        layout.addWidget(QLabel("Последние 10 городов:"))
        self.list_history = QListWidget()
        self.list_history.setMaximumHeight(200)
        layout.addWidget(self.list_history)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        btn_exit = QPushButton("Выход")
        btn_exit.clicked.connect(self.exit_game)
        bottom_layout.addWidget(btn_exit)
        layout.addLayout(bottom_layout)

        self.apply_style()

    def apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QLineEdit {
                padding: 6px;
                font-size: 14px;
            }
            QLabel {
                color: #333;
            }
        """)

    def start_new_game(self):
        first_orig, letter = self.logic.start(self.mode)
        if not first_orig:
            QMessageBox.critical(self, "Ошибка", "Список городов пуст.")
            self.reject()
            return
        self.label_round.setText(f"Компьютер назвал: {first_orig}\nВам на букву: {letter.upper()}")
        self.list_history.clear()
        self.list_history.addItem(f"Компьютер: {first_orig}")
        self.label_score.setText("Очки: 0")
        self.is_finished = False
        self.start_player_turn()

    def start_player_turn(self):
        if self.is_finished:
            return
        self.player_start_time = time.time()
        self.line_edit.clear()
        self.line_edit.setFocus()

        if self.mode == 'super':
            self.remaining_time = SUPER_TIME_LIMIT
            self.label_time.setText(f"⏱ {self.remaining_time} сек")
            self.label_time.setStyleSheet("color: #333;")
            self.super_timer.start(1000)
            self.classic_timer.stop()
        else:
            self.elapsed_time = 0
            self.label_time.setText(f"⏱ 00:00")
            self.label_time.setStyleSheet("color: #333;")
            self.classic_timer.start(1000)
            self.super_timer.stop()

    def update_super_timer(self):
        self.remaining_time -= 1

        if self.remaining_time <= 5:
            self.label_time.setStyleSheet("color: red; font-weight: bold;")
        elif self.remaining_time <= 10:
            self.label_time.setStyleSheet("color: orange; font-weight: bold;")

        self.label_time.setText(f"⏱ {self.remaining_time} сек")

        if self.remaining_time <= 0:
            self.super_timer.stop()
            self.label_time.setText("⏱ 0 сек")
            self.finish_game()

    def update_classic_timer(self):
        self.elapsed_time += 1
        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        self.label_time.setText(f"⏱ {minutes:02d}:{seconds:02d}")

    def submit_city(self):
        if self.is_finished:
            return

        city = self.line_edit.text().strip()
        if not city:
            return

        self.super_timer.stop()
        self.classic_timer.stop()

        elapsed = time.time() - self.player_start_time
        valid, message, score = self.logic.process_player_city(city, elapsed)

        # Проверяем повтор в супер-режиме ПЕРЕД проверкой valid
        if self.logic.repeat_occurred:
            self.super_timer.stop()
            self.classic_timer.stop()
            QMessageBox.information(
                self,
                "Игра окончена",
                f"Вы повторили город. Игра проиграна!\nВаш счёт: {self.logic.total_score} очков"
            )
            self.finish_game()
            return

        if not valid:
            QMessageBox.warning(self, "Ошибка", message)
            if not self.is_finished:
                if self.mode == 'super' and self.remaining_time > 0:
                    self.super_timer.start(1000)
                elif self.mode == 'classic':
                    self.classic_timer.start(1000)
            return

        # Ход корректен
        self.label_score.setText(f"Очки: {self.logic.total_score}")
        self.list_history.addItem(f"Вы: {city} (+{score} очков, {elapsed:.1f}с)")

        comp_city, can_move = self.logic.computer_move()
        if not can_move:
            self.super_timer.stop()
            self.classic_timer.stop()
            self.label_time.setText("⏱ --:--")
            QMessageBox.information(self, "Победа!",
                                    f"Компьютер не может назвать город. Вы выиграли!\nВаши очки: {self.logic.total_score}")
            self.finish_game()
            return

        self.list_history.addItem(f"Компьютер: {comp_city}")
        self.label_round.setText(f"Компьютер назвал: {comp_city}\nВам на букву: {self.logic.current_letter.upper()}")
        self.start_player_turn()

    def exit_game(self):
        if self.is_finished:
            self.reject()
            return
        reply = QMessageBox.question(self, "Выход", "Сохранить текущий результат?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.finish_game()
        else:
            self.reject()

    def finish_game(self):
        if self.is_finished:
            return
        self.is_finished = True
        self.super_timer.stop()
        self.classic_timer.stop()
        self.logic.game_over = True
        self.logic.save_rating(self.mode)
        self.accept()

    def show_rules(self):
        rules_dialog = RulesDialog(self)
        rules_dialog.exec_()


class RatingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Рейтинг")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        top_layout.addStretch()
        btn_exit = QPushButton("Выход")
        btn_exit.clicked.connect(self.close)
        top_layout.addWidget(btn_exit)
        layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Дата", "Очки", "Режим"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.load_data()

        self.apply_style()

    def apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

    def load_data(self):
        rating_file = get_writable_path("rating.json")
        if not os.path.exists(rating_file):
            return
        with open(rating_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.table.setRowCount(len(data))
        for i, entry in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(entry.get("date", "")))
            self.table.setItem(i, 1, QTableWidgetItem(str(entry.get("score", 0))))
            self.table.setItem(i, 2, QTableWidgetItem(entry.get("mode", "")))


class RulesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Правила")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Правила игры «Города»:\n\n"
            "1. Компьютер называет город. Игрок должен назвать город, начинающийся на последнюю букву города компьютера.\n"
            "2. В классическом режиме ограничений по времени нет. В режиме «Супер-города» на ход даётся 30 секунд, "
            "города не должны повторяться. При повторе игра заканчивается проигрышем игрока.\n"
            "3. Нельзя использовать города, которых нет в списке, или которые уже были названы.\n"
            "4. Очки начисляются за быстрый ответ: чем быстрее ответ, тем больше очков (базовая стоимость 100 очков).\n"
            "5. Игра продолжается, пока компьютер не сможет найти подходящий город — в этом случае побеждает игрок.\n"
            "6. При выходе результат сохраняется в таблицу рейтинга.\n"
        )
        layout.addWidget(text)

        btn_back = QPushButton("Назад")
        btn_back.clicked.connect(self.close)
        layout.addWidget(btn_back, alignment=Qt.AlignRight)

        self.apply_style()

    def apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)


# ---------- Запуск ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    main_menu = MainMenu()
    main_menu.show()
    sys.exit(app.exec_())