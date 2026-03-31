import os
import uuid
from PIL import Image
from datetime import datetime


def save_avatar(file, folder):
    """
    Процессинг аватара: генерация имени, обрезка и сжатие.
    Функция гарантирует, что все аватары будут квадратными и небольшого веса.
    """
    if not file or file.filename == '':
        return 'default.png'

    # Генерация уникального идентификатора для имени файла
    extension = file.filename.rsplit('.', 1)[-1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{extension}"
    full_path = os.path.join(folder, unique_filename)

    try:
        # Открытие изображения через библиотеку Pillow
        with Image.open(file) as img:
            width, height = img.size

            # Логика обрезки изображения до центрального квадрата
            min_side = min(width, height)
            left = (width - min_side) / 2
            top = (height - min_side) / 2
            right = (width + min_side) / 2
            bottom = (height + min_side) / 2

            # Выполняем обрезку и ресайз до 300x300 пикселей
            img = img.crop((left, top, right, bottom))
            img.thumbnail((300, 300))

            # Сохранение итогового файла
            img.save(full_path)
            return unique_filename

    except Exception as error:
        # В случае ошибки логируем ее и возвращаем стандартную иконку
        print(f"Критическая ошибка при обработке изображения: {error}")
        return 'default.png'


def check_file_extension(filename, allowed_set={'png', 'jpg', 'jpeg', 'pdf'}):
    """
    Проверка расширения файла на соответствие разрешенному списку.
    Используется для безопасности при загрузке документов.
    """
    if '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in allowed_set
