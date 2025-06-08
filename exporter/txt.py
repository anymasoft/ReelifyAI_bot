from aiogram.types import FSInputFile
from io import StringIO

class TXTExporter:
    @staticmethod
    def export_to_txt(keys: list[tuple[str, int]]) -> FSInputFile:
        output = StringIO()
        for key, count in keys:
            output.write(f"{key}: {count}\n")
        output.seek(0)
        # Создаём временный файл для отправки
        with open("keywords.txt", "w", encoding="utf-8") as f:
            f.write(output.getvalue())
        return FSInputFile("keywords.txt", filename="keywords.txt")