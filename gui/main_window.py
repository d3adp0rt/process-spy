import flet as ft
from typing import List, Optional
from core.process_monitor import ProcessMonitor, ProcessInfo
import threading
import time
from datetime import datetime

class ProcessSpyApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.monitor = ProcessMonitor()
        self.process_list = []
        self.filtered_processes = []
        self.search_term = ""
        self.is_monitoring = False
        
        # UI компоненты
        self.data_table = None
        self.search_field = None
        self.status_text = None
        self.start_stop_btn = None
        self.process_count_text = None
        
        self.setup_page()
        self.create_ui()
        
        # Подписаться на обновления
        self.monitor.add_callback(self.on_processes_updated)
    
    def setup_page(self):
        self.page.title = "Process Spy - Мониторинг процессов"
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
    
    def create_ui(self):
        # Заголовок
        header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.MONITOR_HEART, size=30, color=ft.colors.BLUE),
                ft.Text("Process Spy", size=24, weight=ft.FontWeight.BOLD),
            ]),
            margin=ft.margin.only(bottom=20)
        )
        
        # Панель управления
        self.search_field = ft.TextField(
            label="Поиск процессов...",
            prefix_icon=ft.icons.SEARCH,
            expand=True,
            on_change=self.on_search_change
        )
        
        self.start_stop_btn = ft.ElevatedButton(
            text="Начать мониторинг",
            icon=ft.icons.PLAY_ARROW,
            on_click=self.toggle_monitoring,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN,
                color=ft.colors.WHITE
            )
        )
        
        refresh_btn = ft.ElevatedButton(
            text="Обновить",
            icon=ft.icons.REFRESH,
            on_click=self.refresh_processes
        )
        
        snapshot_btn = ft.ElevatedButton(
            text="Снимок",
            icon=ft.icons.CAMERA_ALT,
            on_click=self.save_snapshot
        )
        
        control_panel = ft.Container(
            content=ft.Row([
                self.search_field,
                self.start_stop_btn,
                refresh_btn,
                snapshot_btn
            ], spacing=10),
            margin=ft.margin.only(bottom=20)
        )
        
        # Информационная панель
        self.status_text = ft.Text("Готов к работе", color=ft.colors.GREEN)
        self.process_count_text = ft.Text("Процессов: 0")
        
        info_panel = ft.Container(
            content=ft.Row([
                self.status_text,
                ft.VerticalDivider(),
                self.process_count_text
            ], spacing=10),
            margin=ft.margin.only(bottom=10)
        )
        
        # Таблица процессов
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("PID")),
                ft.DataColumn(ft.Text("Имя")),
                ft.DataColumn(ft.Text("CPU %")),
                ft.DataColumn(ft.Text("Память %")),
                ft.DataColumn(ft.Text("Статус")),
                ft.DataColumn(ft.Text("Действия"))
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_300),
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_300)
        )
        
        # Контейнер для таблицы с прокруткой
        table_container = ft.Container(
            content=ft.Column([
                self.data_table
            ], scroll=ft.ScrollMode.AUTO),
            expand=True,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
            padding=10
        )
        
        # Добавить все компоненты на страницу
        self.page.add(
            header,
            control_panel,
            info_panel,
            table_container
        )
        
        # Загрузить процессы при старте
        self.refresh_processes()
    
    def on_search_change(self, e):
        self.search_term = e.control.value.lower()
        self.filter_processes()
    
    def filter_processes(self):
        if not self.search_term:
            self.filtered_processes = self.process_list
        else:
            self.filtered_processes = [
                p for p in self.process_list
                if self.search_term in p.name.lower() or 
                   self.search_term in str(p.pid) or
                   any(self.search_term in cmd.lower() for cmd in p.cmdline)
            ]
        
        self.update_table()
    
    def toggle_monitoring(self, e):
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        self.is_monitoring = True
        self.monitor.start_monitoring()
        
        self.start_stop_btn.text = "Остановить мониторинг"
        self.start_stop_btn.icon = ft.icons.STOP
        self.start_stop_btn.style.bgcolor = ft.colors.RED
        self.status_text.value = "Мониторинг активен"
        self.status_text.color = ft.colors.BLUE
        
        self.page.update()
    
    def stop_monitoring(self):
        self.is_monitoring = False
        self.monitor.stop_monitoring()
        
        self.start_stop_btn.text = "Начать мониторинг"
        self.start_stop_btn.icon = ft.icons.PLAY_ARROW
        self.start_stop_btn.style.bgcolor = ft.colors.GREEN
        self.status_text.value = "Мониторинг остановлен"
        self.status_text.color = ft.colors.ORANGE
        
        self.page.update()
    
    def refresh_processes(self, e=None):
        try:
            self.process_list = self.monitor.get_processes()
            self.filter_processes()
            
            if not self.is_monitoring:
                self.status_text.value = "Данные обновлены"
                self.status_text.color = ft.colors.GREEN
                self.page.update()
        except Exception as ex:
            self.status_text.value = f"Ошибка: {str(ex)}"
            self.status_text.color = ft.colors.RED
            self.page.update()
    
    def on_processes_updated(self, processes: List[ProcessInfo]):
        """Callback для обновления из монитора"""
        self.process_list = processes
        self.filter_processes()
        
        # Обновить UI в главном потоке
        def update_ui():
            self.status_text.value = f"Обновлено: {datetime.now().strftime('%H:%M:%S')}"
            self.status_text.color = ft.colors.BLUE
            self.page.update()
        
        self.page.run_thread(update_ui)
    
    def kill_process(self, pid: int):
        def confirm_kill(e):
            if self.monitor.kill_process(pid):
                self.status_text.value = f"Процесс {pid} завершен"
                self.status_text.color = ft.colors.GREEN
                self.refresh_processes()
            else:
                self.status_text.value = f"Не удалось завершить процесс {pid}"
                self.status_text.color = ft.colors.RED
            
            self.page.update()
            dialog.open = False
            self.page.update()
        
        def cancel_kill(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Подтверждение"),
            content=ft.Text(f"Вы уверены, что хотите завершить процесс {pid}?"),
            actions=[
                ft.TextButton("Да", on_click=confirm_kill),
                ft.TextButton("Отмена", on_click=cancel_kill)
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def save_snapshot(self, e):
        try:
            filename = f"process_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.monitor.save_snapshot(filename)
            self.status_text.value = f"Снимок сохранен: {filename}"
            self.status_text.color = ft.colors.GREEN
            self.page.update()
        except Exception as ex:
            self.status_text.value = f"Ошибка сохранения: {str(ex)}"
            self.status_text.color = ft.colors.RED
            self.page.update()
    
    def update_table(self):
        self.data_table.rows.clear()
        
        for process in self.filtered_processes:
            kill_btn = ft.ElevatedButton(
                text="Kill",
                icon=ft.icons.CLOSE,
                on_click=lambda e, pid=process.pid: self.kill_process(pid),
                style=ft.ButtonStyle(
                    bgcolor=ft.colors.RED_100,
                    color=ft.colors.RED
                ),
                height=30
            )
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(process.pid))),
                    ft.DataCell(ft.Text(process.name[:20] + "..." if len(process.name) > 20 else process.name)),
                    ft.DataCell(ft.Text(f"{process.cpu_percent:.1f}%")),
                    ft.DataCell(ft.Text(f"{process.memory_percent:.1f}%")),
                    ft.DataCell(ft.Text(process.status)),
                    ft.DataCell(kill_btn)
                ]
            )
            
            self.data_table.rows.append(row)
        
        self.process_count_text.value = f"Процессов: {len(self.filtered_processes)}"
        self.page.update()