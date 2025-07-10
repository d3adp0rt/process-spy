import flet as ft
from gui.main_window import ProcessSpyApp

def main(page: ft.Page):
    app = ProcessSpyApp(page)

if __name__ == "__main__":
    ft.app(target=main)