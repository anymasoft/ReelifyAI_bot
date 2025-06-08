from typing import List, Tuple
import io
from aiogram.types import InputFile

class TXTExporter:
    @staticmethod
    def export_to_txt(keys: List[Tuple[str, int]]) -> InputFile:
        output = io.StringIO()
        for key, count in keys:
            output.write(f"{key}: {count}\n")
        output.seek(0)
        return InputFile(output, filename="keywords.txt")