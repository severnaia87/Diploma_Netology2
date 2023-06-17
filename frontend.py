# импорты
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from datetime import datetime
from Token import comunity_token, access_token
from bakend import VkTools
from DB_Kinder import check_user, add_user, engine

#отправка сообщений
class BotInterface():
    def __init__(self, comunity_token, access_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(access_token)
        self.params = {}
        self.worksheets = []
        self.keys = []
        self.offset = 0

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def _bdate_toyear(self, bdate):
        user_year = bdate.split('.')[2]
        now = datetime.now().year
        return now - int(user_year)

    def photos_for_send(self, worksheet):
        photos = self.vk_tools.get_photos(worksheet['id'])
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'

        return photo_string

    # g - отличительный параметр, что именно None
    def new_message(self, g):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if g == 0:
                    # Проверка на числа
                    contains_digit = False
                    for k in event.text:
                        if k.isdigit():
                            contains_digit = True
                            break  # Цикл прерван, найдена цифра
                    if contains_digit:
                        self.message_send(event.user_id, 'Пожалуйста, введите имя и фамилию без чисел:')
                    else:
                        return event.text

                if g == 1:
                    if event.text == "1" or event.text == "2":
                        return int(event.text)
                    else:
                        self.message_send(event.user_id, 'Неверный формат ввода пола. Введите 1 или 2:')

                if g == 2:
                    # Проверка на числа
                    contains_digit = False
                    for k in event.text:
                        if k.isdigit():
                            contains_digit = True
                            break  # Цикл прерван, найдена цифра
                    if contains_digit:
                        self.message_send(event.user_id, 'Неверно указан город. Введите название города без чисел:')
                    else:
                        return event.text

                if g == 3:
                    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
                    if not re.match(pattern, event.text):
                        self.message_send(event.user_id, 'Пожалуйста, введите вашу дату рождения в формате (дд.мм.гггг):')
                    else:
                        return self._bdate_toyear(event.text)

    def send_mes_exc(self, event):
        if self.params['name'] is None:
            self.message_send(event.user_id, 'Введите ваше имя и фамилию:')
            return self.new_message(0)

        if self.params['sex'] is None:
            self.message_send(event.user_id, 'Введите свой пол (1-м, 2-ж):')
            return self.new_message(1)

        elif self.params['city'] is None:
            self.message_send(event.user_id, 'Введите город:')
            return self.new_message(2)

        elif self.params['year'] is None:
            self.message_send(event.user_id, 'Введите дату рождения (дд.мм.гггг):')
            return self.new_message(3)

    def get_profile(self, worksheets, event):
        while True:
            if worksheets:
                worksheet = worksheets.pop()

                if not check_user(engine, event.user_id, worksheet['id']): #проверка анкеты в бд в соотвествии с event.user_id
                    add_user(engine, event.user_id, worksheet['id']) #добавить анкету в бд в соотвествии с event.user_id

                    yield worksheet

            else:
                worksheets = self.vk_tools.search_worksheet(
                    self.params, self.offset)

# Обработка событий / получение сообщений

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'привет':
                    ''' Логика для получения данных о пользователе'''
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(event.user_id, f'Здравствуй, путник {self.params["name"]}')

                    # Обрабатываем полноту запроса
                    self.keys = self.params.keys()
                    for k in self.keys:
                        if self.params[k] is None:
                            self.params[k] = self.send_mes_exc(event)

                    self.message_send(event.user_id, 'Вы зарегистрированы!')

                elif event.text.lower() == 'поиск':
                    ''' Логика поиска анкет'''
                    self.message_send(event.user_id, 'Приступаю')
                    msg = next(iter(self.get_profile(self.worksheets, event)))
                    if msg:
                        photo_string = self.photos_for_send(msg)
                        self.offset += 10

                        self.message_send(event.user_id, f'имя: {msg["name"]} ссылка: vk.com/id{msg["id"]}',
                                          attachment=photo_string
                        )

                elif event.text.lower() == 'пока':
                    self.message_send(event.user_id, 'Прощай, путник')
                else:
                    self.message_send(event.user_id, 'Я вас не понимаю')


if __name__ == '__main__':
    bot_interface = BotInterface(comunity_token, access_token)
    bot_interface.event_handler()