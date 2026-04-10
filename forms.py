from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError


class RegistrationForm(FlaskForm):
    """
    Класс формы регистрации нового пользователя.
    Включает проверку длины логина и совпадения паролей.
    """
    username = StringField(
        'Имя пользователя',
        validators=[
            DataRequired(message="Поле логина обязательно для заполнения"),
            Length(min=3, max=20, message="Логин должен быть от 3 до 20 символов")
        ]
    )

    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message="Пароль не может быть пустым"),
            Length(min=6, message="Пароль должен содержать не менее 6 символов")
        ]
    )

    confirm_password = PasswordField(
        'Подтвердите пароль',
        validators=[
            DataRequired(message="Повторите ввод пароля"),
            EqualTo('password', message="Введенные пароли не совпадают")
        ]
    )

    bio = TextAreaField(
        'О себе',
        validators=[Length(max=200, message="Описание слишком длинное")]
    )

    avatar = FileField(
        'Загрузить фото профиля',
        validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Допускаются только изображения!')]
    )

    submit = SubmitField('Зарегистрироваться в системе')


class TripForm(FlaskForm):
    """Форма для планирования новой поездки."""
    city = StringField(
        'Город назначения',
        validators=[DataRequired(message="Укажите город, в который планируете поехать")]
    )

    budget = FloatField(
        'Лимит бюджета (в рублях)',
        validators=[DataRequired(message="Введите числовое значение вашего бюджета")]
    )

    ticket = FileField(
        'Загрузить билет (PDF/JPG)',
        validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Неверный формат документа')]
    )

    submit = SubmitField('Создать новый план поездки')


class ExpenseForm(FlaskForm):
    """Форма для добавления финансовых трат в рамках поездки."""
    amount = FloatField(
        'Сумма расхода (₽)',
        validators=[DataRequired(message="Введите потраченную сумму")]
    )

    category = SelectField(
        'Категория трат',
        choices=[
            ('Еда', 'Питание и продукты'),
            ('Жилье', 'Проживание (отели/хостелы)'),
            ('Транспорт', 'Транспортные расходы'),
            ('Досуг', 'Развлечения и сувениры')
        ]
    )

    description = StringField(
        'Комментарий к расходу',
        validators=[Length(max=100, message="Описание слишком длинное")]
    )

    submit = SubmitField('Зафиксировать расход')