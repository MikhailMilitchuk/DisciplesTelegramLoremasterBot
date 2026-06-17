import json
import requests
import tempfile
import os
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from urllib.parse import urlparse
import re

def handler(event, context):
    try:
        body = json.loads(event['body'])
        
        # Обработка callback_query
        if 'callback_query' in body:
            return handle_callback(body['callback_query'])
        
        # Обработка обычных сообщений
        if 'message' in body and 'text' in body['message']:
            return handle_message(body['message'])
            
    except Exception as e:
        print(f"Error: {e}")
    
    return {'statusCode': 200}

def handle_callback(callback):
    chat_id = callback['message']['chat']['id']
    message_id = callback['message']['message_id']
    callback_data = callback['data']
    
    # Определяем меню по callback_data
    menu_config = get_menu_config(callback_data)
    if menu_config:
        return create_response(chat_id, menu_config['text'], menu_config['keyboard'], message_id)
    
    # Обработка скачивания файла
    if callback_data.startswith('dwld_'):
        return handle_file_download(chat_id, message_id, callback_data[12:], callback_data)
    
    # Обработка юнитов
    if callback_data.startswith('unit_'):
        return handle_unit_info(callback_data, chat_id, message_id)
    
    # Обработка юнитов
    if callback_data.startswith('item_'):
        return handle_item_info(callback_data, chat_id, message_id)

    # Обработка юнитов
    if callback_data.startswith('spel_'):
        return handle_spell_info(callback_data, chat_id, message_id)

    return {'statusCode': 200}

def handle_message(message):
    chat_id = message['chat']['id']
    text = message['text']
    
    if text == "/start" or text == "Вернуться в главное меню":
        return create_response(chat_id, 
                             "Добро пожаловать в архивы Библиотеки Невендаара! Если у вас есть вопросы, предложения или пожелания по работе бота пишите - @rock_wolf. Выберите раздел:",
                             get_menu_config('main_menu')['keyboard'])
    
    elif text.lower().startswith("/unit"):
        response_text = search_unit_info_in_chat(text.lower())
        return create_response(chat_id, response_text, reply_to_message_id=message['message_id'])
    
    return {'statusCode': 200}

def get_menu_config(callback_data):
    menus = {
        'main_menu': {
            'text': "Добро пожаловать в архивы Библиотеки Невендаара! Если у вас есть вопросы, предложения или пожелания по работе бота пишите - @rock_wolf. Выберите раздел:",
            'keyboard': [
                [{'text': 'Disciples Sacred Lands', 'callback_data': 'game_sacred_lands'}],
                [{'text': 'Disciples 2', 'callback_data': 'game_disciples_2'}],
                [{'text': 'Disciples 3', 'callback_data': 'game_disciples_3'}],
                [{'text': 'Disciples Liberation [В ПРОЦЕССЕ]', 'callback_data': 'game_disciples_4'}],
                [{'text': 'Disciples Domination [В ПРОЦЕССЕ]', 'callback_data': 'game_disciples_5'}]
            ]
        },
        'game_disciples_2': {
            'text': "Disciples II - выберите категорию:",
            'keyboard': [
                [{'text': 'Юниты', 'callback_data': 'd2_units'}, {'text': 'Заклинания [В ПРОЦЕССЕ]', 'callback_data': 'd2_spells'}, {'text': 'Предметы [В ПРОЦЕССЕ]', 'callback_data': 'd2_items'}],
                [{'text': 'Сценарии [В ПРОЦЕССЕ]', 'callback_data': 'd2_scenarios'}, {'text': 'Моды [В ПРОЦЕССЕ]', 'callback_data': 'd2_mods'}],
                [{'text': 'Назад', 'callback_data': 'main_menu'}]
            ]
        },
        'game_disciples_3': {
            'text': "Disciples III - выберите категорию:",
            'keyboard': [
                [{'text': 'Юниты [В ПРОЦЕССЕ]', 'callback_data': 'd3_units'}, {'text': 'Заклинания [В ПРОЦЕССЕ]', 'callback_data': 'd3_spells'}, {'text': 'Предметы [В ПРОЦЕССЕ]', 'callback_data': 'd3_items'}],
                [{'text': 'Сценарии [В ПРОЦЕССЕ]', 'callback_data': 'd3_scenarios'}, {'text': 'Моды [В ПРОЦЕССЕ]', 'callback_data': 'd3_mods'}],
                [{'text': 'Назад', 'callback_data': 'main_menu'}]
            ]
        },
        'd2_scenarios': {
            'text': "Disciples II - выберите карту:",
            'keyboard': [
                [{'text': 'Акт 1: Тайна манускрипта', 'callback_data': 'd2_juzz_1'}],
                [{'text': 'Назад', 'callback_data': 'game_disciples_2'}]
            ]
        },
        'game_sacred_lands': {
            'text': "Disciples Sacred Lands - выберите категорию:",
            'keyboard': [
                [{'text': 'Юниты', 'callback_data': 'sacred_units'}, {'text': 'Заклинания [В ПРОЦЕССЕ]', 'callback_data': 'sacred_spells'}, {'text': 'Предметы', 'callback_data': 'sacred_items'}],
                [{'text': 'Сценарии [В ПРОЦЕССЕ]', 'callback_data': 'sacred_scenarios'}, {'text': 'Моды', 'callback_data': 'sacred_mods'}],
                [{'text': 'Назад', 'callback_data': 'main_menu'}]
            ]
        },
        'sacred_mods': {
            'text': "Модификации для Sacred Lands:",
            'keyboard': [
                [{'text': 'Bronze Mod (v1.1)', 'callback_data': 'dwld_mod_d1_BronzeMode.zip'}],
                [{'text': 'Nevendaars Sunny Valley', 'callback_data': 'dwld_mod_d1_NevendaarSunnyValey.zip'}],
                [{'text': 'Назад', 'callback_data': 'game_sacred_lands'}]
            ]
        },
        'sacred_units': {
            'text': "Существа Sacred Lands - выберите фракцию:",
            'keyboard': [
                [{'text': 'Империя', 'callback_data': 'sacred_empire'},{'text': 'Легионы Проклятых', 'callback_data': 'sacred_legions'}],
                [{'text': 'Орды Нежити', 'callback_data': 'sacred_undead'},{'text': 'Горные Кланы', 'callback_data': 'sacred_clans'}],
                [{'text': 'Нейтралы', 'callback_data': 'sacred_neutrals'}],
                [{'text': 'Назад', 'callback_data': 'game_sacred_lands'}]
            ]
        },
        'd2_units': {
            'text': "Существа Disciples II - выберите фракцию:",
            'keyboard': [
                [{'text': 'Империя', 'callback_data': 'd2_empire'},{'text': 'Легионы Проклятых', 'callback_data': 'd2_legions'}],
                [{'text': 'Орды Нежити', 'callback_data': 'd2_undead'},{'text': 'Горные Кланы', 'callback_data': 'd2_clans'}],
                [{'text': 'Эльфийский Альянс', 'callback_data': 'd2_elves'},{'text': 'Нейтралы', 'callback_data': 'd2_neutrals'}],
                [{'text': 'Назад', 'callback_data': 'game_disciples_2'}]
            ]
        },
        'sacred_items': {
            'text': "Предметы Sacred Lands - выберите тип:",
            'keyboard': [
                [{'text': 'Артефакты', 'callback_data': 'sacred_artefacts'},{'text': 'Книги', 'callback_data': 'sacred_books'},{'text': 'Знамена', 'callback_data': 'sacred_banners'}],
                [{'text': 'Посохи [В ПРОЦЕССЕ]', 'callback_data': 'sacred_staffs'},{'text': 'Зелья [В ПРОЦЕССЕ]', 'callback_data': 'sacred_potions'},{'text': 'Свитки [В ПРОЦЕССЕ]', 'callback_data': 'scrolls'}],
                [{'text': 'Драгоценности', 'callback_data': 'sacred_values'}],
                [{'text': 'Назад', 'callback_data': 'game_sacred_lands'}]
            ]
        },
        'sacred_artefacts': {
            'text': "Артефакты Sacred Lands:",
            'keyboard': [
                [{'text': 'Рунный камень', 'callback_data': 'item_arts_РунныйКаменьД1'},{'text': 'Рунный клинок', 'callback_data': 'item_arts_РунныйКлинокД1'}],
                [{'text': 'Священная чаша', 'callback_data': 'item_arts_СвященнаяЧашаД1'},{'text': 'Нечестивая чаша', 'callback_data': 'item_arts_НечестиваяЧашаД1'}],
                [{'text': 'Наручи с черепами', 'callback_data': 'item_arts_НаручисЧерепамиД1'},{'text': 'Кровавый меч', 'callback_data': 'item_arts_КровавыйМечД1'}],
                [{'text': 'Рог отваги', 'callback_data': 'item_arts_РогОтвагиД1'},{'text': 'Коготь Мортис', 'callback_data': 'item_arts_КоготьМортисД1'}],
                [{'text': 'Драконий щит', 'callback_data': 'item_arts_ДраконийЩитД1'},{'text': 'Молот Мьёлнир', 'callback_data': 'item_arts_МолотМьёлнирД1'}],
                [{'text': 'Меч веков', 'callback_data': 'item_arts_МечВековД1'},{'text': 'Коготь Бетрезена', 'callback_data': 'item_arts_КоготьБетрезенаД1'}],
                [{'text': 'Шлем непорочности', 'callback_data': 'item_arts_ШлемНепорочностиД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_items'}]
            ]
        },
        'sacred_books': {
            'text': "Книги Sacred Lands:",
            'keyboard': [
                [{'text': 'Фолиант воздуха', 'callback_data': 'item_toms_ФолиантВоздухаД1'},{'text': 'Фолиант воды', 'callback_data': 'item_toms_ФолиантВодыД1'}],
                [{'text': 'Фолиант земли', 'callback_data': 'item_toms_ФолиантВЗемлиД1'},{'text': 'Фолиант огня', 'callback_data': 'item_toms_ФолиантОгняД1'}],
                [{'text': 'Фолиант эльфийский знаний', 'callback_data': 'item_toms_ФолиантЭльфийскийЗнанийД1'},{'text': 'Фолиант семи ветров', 'callback_data': 'item_toms_ФолиантСемиВетровД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_items'}]
            ]
        },
        'sacred_banners': {
            'text': "Знамёна Sacred Lands:",
            'keyboard': [
                [{'text': 'Знамя защиты', 'callback_data': 'item_bnrs_ЗнамяЗащитыД1'},{'text': 'Знамя сопротивления', 'callback_data': 'item_bnrs_ЗнамяСопротивленияД1'}],
                [{'text': 'Знамя скорости', 'callback_data': 'item_bnrs_ЗнамяСкоростиД1'},{'text': 'Знамя стремительности', 'callback_data': 'item_bnrs_ЗнамяСтремительностиД1'}],
                [{'text': 'Знамя сражения', 'callback_data': 'item_bnrs_ЗнамяСраженияД1'},{'text': 'Знамя войны', 'callback_data': 'item_bnrs_ЗнамяВойныД1'}],
                [{'text': 'Знамя силы', 'callback_data': 'item_bnrs_ЗнамяСилыД1'},{'text': 'Знамя мощи', 'callback_data': 'item_bnrs_ЗнамяМощиД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_items'}]
            ]
        },
        'sacred_values': {
            'text': "Драгоценности Sacred Lands:",
            'keyboard': [
                [{'text': 'Бронзовое кольцо', 'callback_data': 'item_vals_БронзовоеКольцоД1'},{'text': 'Серебрянное кольцо', 'callback_data': 'item_vals_СеребрянноеКольцоД1'},{'text': 'Золотое кольцо', 'callback_data': 'item_vals_ЗолотоеКольцоД1'}],
                [{'text': 'Изумруд', 'callback_data': 'item_vals_ИзумрудД1'},{'text': 'Рубин', 'callback_data': 'item_vals_РубинД1'},{'text': 'Сапфир', 'callback_data': 'item_vals_СапфирД1'},{'text': 'Алмаз', 'callback_data': 'item_vals_АлмазД1'}],
                [{'text': 'Древняя реликвия', 'callback_data': 'item_vals_ДревняяРеликвияД1'},{'text': 'Королевский скипетр', 'callback_data': 'item_vals_КоролевскийСкипетрД1'},{'text': 'Императорская корона', 'callback_data': 'item_vals_ИмператорскаяКоронаД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_items'}]
            ]
        },
        'sacred_neutrals': {
            'text': "Нейтральные существа - выберите подфракцию:",
            'keyboard': [
                [{'text': 'Люди', 'callback_data': 'sacred_humans'},{'text': 'Эльфы', 'callback_data': 'sacred_elves'}],
                [{'text': 'Зеленокожие', 'callback_data': 'sacred_orcs'},{'text': 'Нечисть', 'callback_data': 'sacred_evils'}],
                [{'text': 'Мерфолки', 'callback_data': 'sacred_merfolks'},{'text': 'Обитатели болот', 'callback_data': 'sacred_march'}],
                [{'text': 'Драконы', 'callback_data': 'sacred_dragons'}, {'text': 'Уникальные персонажи', 'callback_data': 'sacred_bosses'}],
                [{'text': 'Назад', 'callback_data': 'sacred_units'}]
            ]
        },
        'd2_neutrals': {
            'text': "Нейтральные существа - выберите подфракцию:",
            'keyboard': [
                [{'text': 'Люди', 'callback_data': 'd2_humans'},{'text': 'Эльфы', 'callback_data': 'd2_neutral_elves'},{'text': 'Гномы', 'callback_data': 'd2_dwarfs'}],
                [{'text': 'Варвары', 'callback_data': 'd2_barbarians'},{'text': 'Зеленокожие', 'callback_data': 'd2_orcs'}],
                [{'text': 'Темные эльфы', 'callback_data': 'd2_darkelves'},{'text': 'Нежить', 'callback_data': 'd2_neutrals_undead'}],
                [{'text': 'Животные', 'callback_data': 'd2_animals'},{'text': 'Чудовища', 'callback_data': 'd2_monsters'}],
                [{'text': 'Мерфолки', 'callback_data': 'd2_merfolks'},{'text': 'Обитатели болот', 'callback_data': 'd2_march'}],
                [{'text': 'Драконы', 'callback_data': 'd2_dragons'}, {'text': 'Уникальные персонажи', 'callback_data': 'd2_bosses'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'd2_barbarians': {
            'text': "Северные варвары - выберите существо:",
            'keyboard': [
                [{'text': 'Воин-варвар', 'callback_data': 'unit_neu_barb_ВоинВарварД2'}],
                [{'text': 'Ловчий', 'callback_data': 'unit_neu_barb_ЛовчийД2'}],
                [{'text': 'Шаманка', 'callback_data': 'unit_neu_barb_ШаманкаД2'}],
                [{'text': 'Вождь варваров', 'callback_data': 'unit_neu_barb_ВождьВарваровД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_humans': {
            'text': "Нейтральные люди - выберите существо:",
            'keyboard': [
                [{'text': 'Крестьянин', 'callback_data': 'unit_neu_humn_КрестьянинД2'}],
                [{'text': 'Разбойник', 'callback_data': 'unit_neu_humn_РазбойникД2'},{'text': 'Головорез', 'callback_data': 'unit_neu_humn_ГоловорезД2'}],
                [{'text': 'Ополченец', 'callback_data': 'unit_neu_humn_ОполченецД2'},{'text': 'Копейщик', 'callback_data': 'unit_neu_humn_КопейщикД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'sacred_humans': {
            'text': "Нейтральные люди - выберите существо:",
            'keyboard': [
                [{'text': 'Крестьянин', 'callback_data': 'unit_neu_humn_КрестьянинД1'},{'text': 'Бандит', 'callback_data': 'unit_neu_humn_БандитД1'}],
                [{'text': 'Наемник', 'callback_data': 'unit_neu_humn_НаемникД1'},{'text': 'Копейщик', 'callback_data': 'unit_neu_humn_КопейщикД1'}],
                [{'text': 'Варвар', 'callback_data': 'unit_neu_humn_ВарварД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'sacred_elves': {
            'text': "Эльфы - выберите существо:",
            'keyboard': [
                [{'text': 'Лесной эльф', 'callback_data': 'unit_neu_elvs_ЛеснойЭльфД1'},{'text': 'Эльф рейнджер', 'callback_data': 'unit_neu_elvs_ЭльфРейнджерД1'}, {'text': 'Эльфийский оракул', 'callback_data': 'unit_neu_elvs_ЭльфОракулД1'}],
                [{'text': 'Лорд эльфов', 'callback_data': 'unit_neu_elvs_ЛордЭльфовД1'},{'text': 'Эльфийская принцесса', 'callback_data': 'unit_neu_elvs_ЭльфийскаяПринцессаД1'}],
                [{'text': 'Кентавр', 'callback_data': 'unit_neu_elvs_КентаврД1'}, {'text': 'Кентавр-копейщик', 'callback_data': 'unit_neu_elvs_КентаврКопейщикД1'}],
                [{'text': 'Грифон', 'callback_data': 'unit_neu_elvs_ГрифонД1'}, {'text': 'Владыка небес', 'callback_data': 'unit_neu_elvs_ВладыкаНебесД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'd2_neutral_elves': {
            'text': "Эльфы - выберите существо:",
            'keyboard': [
                [{'text': 'Лесной эльф', 'callback_data': 'unit_neu_elvs_ЛеснойЭльфД2'},{'text': 'Эльф следопыт', 'callback_data': 'unit_neu_elvs_ЭльфСледопытД2'}],
                [{'text': 'Эльф оракул', 'callback_data': 'unit_neu_elvs_ЭльфОракулД2'},{'text': 'Повелитель эльфов', 'callback_data': 'unit_neu_elvs_ПовелительЭльфовД2'}],
                [{'text': 'Кентавр', 'callback_data': 'unit_neu_elvs_КентаврД2'}, {'text': 'Кентавр-копейщик', 'callback_data': 'unit_neu_elvs_НейтралКентаврКопейщикД2'}],
                [{'text': 'Грифон', 'callback_data': 'unit_neu_elvs_НейтральныйГрифонД2'}, {'text': 'Владыка небес', 'callback_data': 'unit_neu_elvs_НейтралВладыкаНебесД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_dwarfs': {
            'text': "Гномы - выберите существо:",
            'keyboard': [
                [{'text': 'Верховный король гномов', 'callback_data': 'unit_neu_dwrf_ВерховныйКорольГномовД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_orcs': {
            'text': "Зеленокожие - выберите существо:",
            'keyboard': [
                [{'text': 'Гоблин', 'callback_data': 'unit_neu_orcs_ГоблинД2'},{'text': 'Гоблин-лучник', 'callback_data': 'unit_neu_orcs_ГоблинЛучникД2'},{'text': 'Старейшина гоблинов', 'callback_data': 'unit_neu_orcs_СтарейшинаГоблиновД2'}],
                [{'text': 'Орк', 'callback_data': 'unit_neu_orcs_ОркД2'},{'text': 'Вождь орков', 'callback_data': 'unit_neu_orcs_ВождьОрковД2'},{'text': 'Король орков', 'callback_data': 'unit_neu_orcs_КорольОрковД2'}],
                [{'text': 'Людоед', 'callback_data': 'unit_neu_orcs_ЛюдоедД2'}, {'text': 'Тролль', 'callback_data': 'unit_neu_orcs_ТролльД2'}, {'text': 'Циклоп', 'callback_data': 'unit_neu_orcs_ЦиклопД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_darkelves': {
            'text': "Темные эльфы - выберите существо:",
            'keyboard': [
                [{'text': 'Темный эльф-мясник', 'callback_data': 'unit_neu_drks_ТемныйЭльфМясникД2'},{'text': 'Темный эльф-жнец', 'callback_data': 'unit_neu_drks_ТемныйЭльфЖнецД2'}],
                [{'text': 'Темный эльф-жрица', 'callback_data': 'unit_neu_drks_ТемныйЭльфЖрицаД2'},{'text': 'Темный эльф-призрак', 'callback_data': 'unit_neu_drks_ТемныйЭльфПризракД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_neutrals_undead': {
            'text': "Нежить - выберите существо:",
            'keyboard': [
                [{'text': 'Упырь', 'callback_data': 'unit_neu_unds_УпырьД2'},{'text': 'Волк-призрак', 'callback_data': 'unit_neu_unds_ВолкПризракД2'}],
                [{'text': 'Оккультист', 'callback_data': 'unit_neu_unds_ОккультистД2'},{'text': 'Мастер-оккультист', 'callback_data': 'unit_neu_unds_МастерОккультистД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_animals': {
            'text': "Животные - выберите существо:",
            'keyboard': [
                [{'text': 'Волк', 'callback_data': 'unit_neu_anml_ВолкД2'}],
                [{'text': 'Бурый медведь', 'callback_data': 'unit_neu_anml_БурыйМедведьД2'}],
                [{'text': 'Белый медведь', 'callback_data': 'unit_neu_anml_БелыйМедведьД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_monsters': {
            'text': "Чудовища - выберите существо:",
            'keyboard': [
                [{'text': 'Гигантский паук', 'callback_data': 'unit_neu_mnst_ГигантскийПаукД2'}],
                [{'text': 'Гигантский черный паук', 'callback_data': 'unit_neu_mnst_ГигантскийЧерныйПаукД2'}],
                [{'text': 'Мантикора', 'callback_data': 'unit_neu_mnst_МантикораД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'sacred_orcs': {
            'text': "Зеленокожие - выберите существо:",
            'keyboard': [
                [{'text': 'Гоблин', 'callback_data': 'unit_neu_orcs_ГоблинД1'},{'text': 'Гигантский паук', 'callback_data': 'unit_neu_orcs_ГигантскийПаукД1'}],
                [{'text': 'Орк', 'callback_data': 'unit_neu_orcs_ОркД1'},{'text': 'Орк-чемпион', 'callback_data': 'unit_neu_orcs_ОркЧемпионД1'},{'text': 'Король орков', 'callback_data': 'unit_neu_orcs_КорольОрковД1'}],
                [{'text': 'Огр', 'callback_data': 'unit_neu_orcs_ОгрД1'}, {'text': 'Тролль', 'callback_data': 'unit_neu_orcs_ТролльД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'sacred_evils': {
            'text': "Нечисть - выберите существо:",
            'keyboard': [
                [{'text': 'Упырь', 'callback_data': 'unit_neu_evil_УпырьД1'},{'text': 'Скелет', 'callback_data': 'unit_neu_evil_СкелетСтрелокД1'}],
                [{'text': 'Бес', 'callback_data': 'unit_neu_evil_БесД1'}, {'text': 'Страж дьявола', 'callback_data': 'unit_neu_evil_СтражДьяволаД1'}],
                [{'text': 'Элементаль огня', 'callback_data': 'unit_neu_evil_ЭлементальОгняД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'sacred_merfolks': {
            'text': "Мерфолки - выберите существо:",
            'keyboard': [
                [{'text': 'Тритон', 'callback_data': 'unit_neu_merf_ТритонД1'},{'text': 'Русалка', 'callback_data': 'unit_neu_merf_РусалкаД1'}],
                [{'text': 'Кракен', 'callback_data': 'unit_neu_merf_КракенД1'}, {'text': 'Морской змей', 'callback_data': 'unit_neu_merf_МорскойЗмейД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'sacred_march': {
            'text': "Обитатели болот - выберите существо:",
            'keyboard': [
                [{'text': 'Человек-ящер', 'callback_data': 'unit_neu_mrch_ЧеловекЯщерД1'}],
                [{'text': 'Медуза', 'callback_data': 'unit_neu_mrch_МедузаД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'sacred_dragons': {
            'text': "Драконы - выберите существо:",
            'keyboard': [
                [{'text': 'Зеленый дракон', 'callback_data': 'unit_neu_drgn_ЗеленыйДраконД1'},{'text': 'Синий дракон', 'callback_data': 'unit_neu_drgn_СинийДраконД1'}],
                [{'text': 'Белый дракон', 'callback_data': 'unit_neu_drgn_БелыйДраконД1'},{'text': 'Красный дракон', 'callback_data': 'unit_neu_drgn_КрасныйДраконД1'}],
                [{'text': 'Черный дракон', 'callback_data': 'unit_neu_drgn_ЧерныйДраконД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'd2_merfolks': {
            'text': "Мерфолки - выберите существо:",
            'keyboard': [
                [{'text': 'Тритон', 'callback_data': 'unit_neu_merf_ТритонД2'},{'text': 'Русалка', 'callback_data': 'unit_neu_merf_РусалкаД2'}],
                [{'text': 'Кракен', 'callback_data': 'unit_neu_merf_КракенД2'}, {'text': 'Морской змей', 'callback_data': 'unit_neu_merf_МорскойЗмейД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_march': {
            'text': "Обитатели болот - выберите существо:",
            'keyboard': [
                [{'text': 'Человек-ящер', 'callback_data': 'unit_neu_mrch_ЧеловекЯщерД2'}],
                [{'text': 'Медуза', 'callback_data': 'unit_neu_mrch_МедузаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'd2_dragons': {
            'text': "Драконы - выберите существо:",
            'keyboard': [
                [{'text': 'Зеленый дракон', 'callback_data': 'unit_neu_drgn_ЗеленыйДраконД2'},{'text': 'Синий дракон', 'callback_data': 'unit_neu_drgn_СинийДраконД2'}],
                [{'text': 'Белый дракон', 'callback_data': 'unit_neu_drgn_БелыйДраконД2'},{'text': 'Красный дракон', 'callback_data': 'unit_neu_drgn_КрасныйДраконД2'}],
                [{'text': 'Черный дракон', 'callback_data': 'unit_neu_drgn_ЧерныйДраконД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'sacred_bosses': {
            'text': "Уникальные персонажи - выберите нужного:",
            'keyboard': [
                [{'text': 'Бернар де Каузак', 'callback_data': 'unit_neu_boss_БернарДеКаузакД1'}],
                [{'text': 'Хель', 'callback_data': 'unit_neu_boss_ХельД1'}],
                [{'text': 'Дорагон', 'callback_data': 'unit_neu_boss_ДорагонД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_neutrals'}]
            ]
        },
        'd2_bosses': {
            'text': "Уникальные персонажи - выберите нужного:",
            'keyboard': [
                [{'text': 'Утер', 'callback_data': 'unit_neu_boss_УтерД2'}, {'text': 'Юбер де Лали', 'callback_data': 'unit_neu_boss_ЮберДеЛалиД2'}],
                [{'text': 'Граф Фламель Кроули', 'callback_data': 'unit_neu_boss_ГрафФламельКроулиД2'}, {'text': 'Сир Аллемон', 'callback_data': 'unit_neu_boss_СирАллемонД2'}],
                [{'text': 'Эрхог Темная', 'callback_data': 'unit_neu_boss_ЭрхогТемнаяД2'},{'text': 'Некромант Эрхог', 'callback_data': 'unit_neu_boss_НекромантЭрхогД2'}],
                [{'text': 'Темный эльф Лиф', 'callback_data': 'unit_neu_boss_ЛифД2'},{'text': 'Темный Лаклаан', 'callback_data': 'unit_neu_boss_ТемныйЛаклаанД2'}],
                [{'text': 'Костяной лорд', 'callback_data': 'unit_neu_boss_КостянойЛордД2'},{'text': 'Могильный голем', 'callback_data': 'unit_neu_boss_МогильныйГолемД2'}],
                [{'text': 'Дрега Зул', 'callback_data': 'unit_neu_boss_ДрегаЗулД2'}],
                [{'text': 'Королева эльфов', 'callback_data': 'unit_neu_boss_КоролеваЭльфовД2'},{'text': 'Лаклаан', 'callback_data': 'unit_neu_boss_ЛаклаанД2'}],
                [{'text': 'Друллиаан', 'callback_data': 'unit_neu_boss_ДруллиаанД2'},{'text': 'Зверь Галлеана', 'callback_data': 'unit_neu_boss_ЗверьГаллеанаД2'}],
                [{'text': 'ЯатаХалли', 'callback_data': 'unit_neu_boss_ЯатаХаллиД2'},{'text': 'Гумтик Кровавый', 'callback_data': 'unit_neu_boss_ГумтикКровавыйД2'}],
                [{'text': 'Маг Хугин', 'callback_data': 'unit_neu_boss_ХугинД2'},{'text': 'Нидхегг', 'callback_data': 'unit_neu_boss_НидхеггД2'}],
                [{'text': 'Одержимый Утер', 'callback_data': 'unit_neu_boss_ОдержимыйУтерД2'},{'text': 'Демон Утер', 'callback_data': 'unit_neu_boss_ДемонУтерД2'}],
                [{'text': 'Астарот', 'callback_data': 'unit_neu_boss_АстаротД2'},{'text': 'Небирос', 'callback_data': 'unit_neu_boss_НебиросД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_neutrals'}]
            ]
        },
        'sacred_empire': {
            'text': "Империя - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'empire_heroes_d1'}, {'text': 'Страж Столицы', 'callback_data': 'unit_emp_grdn_МизраэльД1'}],
                [{'text': 'Воины', 'callback_data': 'empire_warriors_d1'}, {'text': 'Стрелки', 'callback_data': 'empire_archers_d1'}, {'text': 'Маги', 'callback_data': 'empire_mages_d1'}, {'text': 'Поддержка', 'callback_data': 'empire_support_d1'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_emp_spcl_ТитанД1'}, {'text': 'Призываемые существа', 'callback_data': 'empire_summoned_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_units'}]
            ]
        },
        'd2_empire': {
            'text': "Империя - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'empire_heroes_d2'}, {'text': 'Страж Столицы', 'callback_data': 'unit_emp_grdn_МизраэльД2'}],
                [{'text': 'Воины', 'callback_data': 'unit_emp_warr_ВоиныИмперииД2'}, {'text': 'Стрелки', 'callback_data': 'unit_emp_arch_СтрелкиИмперииД2'}, {'text': 'Маги', 'callback_data': 'empire_mages_d2'}, {'text': 'Поддержка', 'callback_data': 'empire_support_d2'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_emp_spcl_ТитанД2'}, {'text': 'Призываемые существа', 'callback_data': 'empire_summoned_d2'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'd2_elves': {
            'text': "Эльфийский Альянс - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'elves_heroes_d2'}, {'text': 'Страж Столицы', 'callback_data': 'unit_elf_grdn_ИллюмиэльД2'}],
                [{'text': 'Воины', 'callback_data': 'elves_warriors_d2'}, {'text': 'Стрелки', 'callback_data': 'elves_archers_d2'}, {'text': 'Маги', 'callback_data': 'elves_mages_d2'}, {'text': 'Поддержка', 'callback_data': 'elves_support_d2'}],
                [{'text': 'Особые существа', 'callback_data': 'elves_specials_d2'}, {'text': 'Призываемые существа', 'callback_data': 'elves_summoned_d2'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'elves_heroes_d2': {
            'text': "Герои Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Вассал Леса', 'callback_data': 'unit_elf_hero_ВассалЛесаД2'}, {'text': 'Дриада', 'callback_data': 'unit_elf_hero_ДриадаД2'}, {'text': 'Защитник', 'callback_data': 'unit_elf_hero_ЗащитникД2'}],
                [{'text': 'Мудрец', 'callback_data': 'unit_elf_hero_МудрецД2'}, {'text': 'Вор', 'callback_data': 'unit_elf_hero_ВорЭльфовД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'empire_heroes_d1': {
            'text': "Герои Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Рыцарь на Пегасе', 'callback_data': 'unit_emp_hero_РыцарьПегасаД1'}, {'text': 'Архимаг', 'callback_data': 'unit_emp_hero_АрхимагД1'}, {'text': 'Рейнджер', 'callback_data': 'unit_emp_hero_РейнджерД1'}],
                [{'text': 'Архангел', 'callback_data': 'unit_emp_hero_АрхангелД1'}, {'text': 'Вор', 'callback_data': 'unit_emp_hero_ВорИмперииД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_heroes_d2': {
            'text': "Герои Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Рыцарь на Пегасе', 'callback_data': 'unit_emp_hero_РыцарьНаПегасеД2'}, {'text': 'Архимаг', 'callback_data': 'unit_emp_hero_АрхимагД2'}, {'text': 'Следопыт', 'callback_data': 'unit_emp_hero_СледопытД2'}],
                [{'text': 'Архангел', 'callback_data': 'unit_emp_hero_АрхангелД2'}, {'text': 'Вор', 'callback_data': 'unit_emp_hero_ВорИмперииД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'empire_warriors_d1': {
            'text': "Воины Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Боец', 'callback_data': 'unit_emp_warr_МечникД1'}],
                [{'text': 'Рыцарь', 'callback_data': 'unit_emp_warr_РыцарьД1'}, {'text': '-', 'callback_data': 'empire_warriors_d1'},{'text': 'Охотник на ведьм', 'callback_data': 'unit_emp_warr_ОхотникНаВедьмД1'}],
                [{'text': 'Имперский рыцарь', 'callback_data': 'unit_emp_warr_РыцарьИмперииД1'}, {'text': '-', 'callback_data': 'empire_warriors_d1'}, {'text': 'Инквизитор', 'callback_data': 'unit_emp_warr_ИнквизиторД1'}],
                [{'text': 'Паладин', 'callback_data': 'unit_emp_warr_ПаладинД1'}, {'text': 'Ангел', 'callback_data': 'unit_emp_warr_АнгелД1'}, {'text': '-', 'callback_data': 'empire_warriors_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_warriors_d2': {
            'text': "Воины Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Сквайр', 'callback_data': 'unit_emp_warr_СквайрД2'}],
                [{'text': 'Рыцарь', 'callback_data': 'unit_emp_warr_РыцарьД2'},{'text': 'Охотник на ведьм', 'callback_data': 'unit_emp_warr_ОхотникНаВедьмД2'}],
                [{'text': 'Имперский рыцарь', 'callback_data': 'unit_emp_warr_РыцарьИмперииД2'}, {'text': 'Инквизитор', 'callback_data': 'unit_emp_warr_ИнквизиторД2'}],
                [{'text': 'Паладин', 'callback_data': 'unit_emp_warr_ПаладинД2'}, {'text': 'Ангел', 'callback_data': 'unit_emp_warr_АнгелД2'}, {'text': 'Великий инквизитор', 'callback_data': 'unit_emp_warr_ВеликийИнквизиторД2'}],
                [{'text': 'Защитник веры', 'callback_data': 'unit_emp_warr_ЗащитникВерыД2'}, {'text': 'Святой мститель', 'callback_data': 'unit_emp_warr_СвятойМстительД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'elves_warriors_d2': {
            'text': "Воины Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Кентавр-копейщик', 'callback_data': 'unit_elf_warr_КентаврКопейщикД2'}],
                [{'text': 'Кентавр странник', 'callback_data': 'unit_elf_warr_КентаврСтранникД2'},{'text': 'Кентавр латник', 'callback_data': 'unit_elf_warr_КентаврЛатникД2'}],
                [{'text': 'Дикий кентавр', 'callback_data': 'unit_elf_warr_ДикийКентаврД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'empire_mages_d1': {
            'text': "Маги Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Ученик', 'callback_data': 'unit_emp_mage_УченикД1'}],
                [{'text': 'Маг', 'callback_data': 'unit_emp_mage_МагД1'}],
                [{'text': 'Волшебник', 'callback_data': 'unit_emp_mage_ВолшебникД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_mages_d2': {
            'text': "Маги Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Ученик', 'callback_data': 'unit_emp_mage_УченикД2'}],
                [{'text': 'Волшебник', 'callback_data': 'unit_emp_mage_ВолшебникД2'}],
                [{'text': 'Маг', 'callback_data': 'unit_emp_mage_МагД2'},{'text': 'Элементалист', 'callback_data': 'unit_emp_mage_ЭлементалистД2'}],
                [{'text': 'Белый маг', 'callback_data': 'unit_emp_mage_БелыйМагД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'elves_mages_d2': {
            'text': "Маги Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Адепт', 'callback_data': 'unit_elf_mage_АдептЭльфовД2'}],
                [{'text': 'Громобой', 'callback_data': 'unit_elf_mage_ГромобойД2'}],
                [{'text': 'Архонт', 'callback_data': 'unit_elf_mage_АрхонтД2'},{'text': 'Теург', 'callback_data': 'unit_elf_mage_ТеургД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'empire_archers_d1': {
            'text': "Стрелки Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Лучник', 'callback_data': 'unit_emp_arch_ЛучникД1'}],
                [{'text': 'Стрелок', 'callback_data': 'unit_emp_arch_СтрелокД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_archers_d2': {
            'text': "Стрелки Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Лучник', 'callback_data': 'unit_emp_arch_ЛучникД2'}],
                [{'text': 'Стрелок', 'callback_data': 'unit_emp_arch_СтрелокД2'}],
                [{'text': 'Ассасин империи', 'callback_data': 'unit_emp_arch_АссасинИмперииД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'elves_archers_d2': {
            'text': "Стрелки Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Разведчик', 'callback_data': 'unit_elf_arch_РазведчикД2'}],
                [{'text': 'Охотник', 'callback_data': 'unit_elf_arch_ОхотникД2'}, {'text': 'Дозорный', 'callback_data': 'unit_elf_arch_ДозорныйД2'}],
                [{'text': 'Бандит', 'callback_data': 'unit_elf_arch_БандитД2'}, {'text': 'Шершень', 'callback_data': 'unit_elf_arch_ШершеньД2'}, {'text': 'Смотритель', 'callback_data': 'unit_elf_arch_СмотрительД2'}, {'text': 'Часовой', 'callback_data': 'unit_elf_arch_ЧасовойД2'}],
                [{'text': 'Разбойник', 'callback_data': 'unit_elf_arch_РазбойникЭльфовД2'}],
                [{'text': 'Мародер', 'callback_data': 'unit_elf_arch_МародерД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'empire_support_d1': {
            'text': "Поддержка Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Служка', 'callback_data': 'unit_emp_supp_СлужкаД1'}],
                [{'text': 'Священник', 'callback_data': 'unit_emp_supp_СвященникД1'},{'text': 'Монах', 'callback_data': 'unit_emp_supp_МонахД1'}],
                [{'text': 'Священник Империи', 'callback_data': 'unit_emp_supp_СвященникИмперииД1'},{'text': 'Патриарх', 'callback_data': 'unit_emp_supp_ПатриархД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_support_d2': {
            'text': "Поддержка Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Служка', 'callback_data': 'unit_emp_supp_СлужкаД2'}],
                [{'text': 'Священник', 'callback_data': 'unit_emp_supp_СвященникД2'},{'text': 'Монахиня', 'callback_data': 'unit_emp_supp_МонахиняД2'}],
                [{'text': 'Священник Империи', 'callback_data': 'unit_emp_supp_СвященникИмперииД2'},{'text': 'Матриарх', 'callback_data': 'unit_emp_supp_МатриархД2'}],
                [{'text': 'Патриарх', 'callback_data': 'unit_emp_supp_ПатриархД2'},{'text': 'Прорицательница', 'callback_data': 'unit_emp_supp_ПрорицательницаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'elves_support_d2': {
            'text': "Поддержка Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Медиум', 'callback_data': 'unit_elf_supp_МедиумД2'}],
                [{'text': 'Оракул', 'callback_data': 'unit_elf_supp_ОракулД2'}],
                [{'text': 'Дева Рощи', 'callback_data': 'unit_elf_supp_ДеваРощиД2'}],
                [{'text': 'Солнечная танцовщица', 'callback_data': 'unit_elf_supp_СолнечнаяТанцовщицаД2'},{'text': 'Сильфида', 'callback_data': 'unit_elf_supp_СильфидаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'empire_summoned_d1': {
            'text': "Призываемые существа Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Живой доспех', 'callback_data': 'unit_emp_smnd_ЖивойДоспехД1'}],
                [{'text': 'Голем', 'callback_data': 'unit_emp_smnd_ГолемД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_empire'}]
            ]
        },
        'empire_summoned_d2': {
            'text': "Призываемые существа Империи - выберите юнита:",
            'keyboard': [
                [{'text': 'Оживший доспех', 'callback_data': 'unit_emp_smnd_МагическийДоспехД2'}],
                [{'text': 'Голем', 'callback_data': 'unit_emp_smnd_ГолемД2'}],
                [{'text': 'Элементаль воздуха', 'callback_data': 'unit_emp_mage_ЭлементальВоздухаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_empire'}]
            ]
        },
        'elves_summoned_d2': {
            'text': "Призываемые существа Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Малый энт', 'callback_data': 'unit_elf_smnd_МалыйЭнтД2'}],
                [{'text': 'Энт', 'callback_data': 'unit_elf_smnd_ЭнтД2'}],
                [{'text': 'Великий энт', 'callback_data': 'unit_elf_smnd_ВеликийЭнтД2'}],
                [{'text': 'Страж рощи', 'callback_data': 'unit_elf_smnd_СтражРощиД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        },
        'sacred_legions': {
            'text': "Легионы Проклятых - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'legion_heroes_d1'}, {'text': 'Страж Столицы', 'callback_data': 'unit_lgn_grdn_АшкаэльД1'}],
                [{'text': 'Воины', 'callback_data': 'legion_warriors_d1'}, {'text': 'Стрелки', 'callback_data': 'legion_archers_d1'}, {'text': 'Маги', 'callback_data': 'legion_mages_d1'}, {'text': 'Поддержка', 'callback_data': 'legion_support_d1'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_lgn_spcl_ИзвергД1'}, {'text': 'Призываемые существа', 'callback_data': 'legion_summoned_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_units'}]
            ]
        },
        'd2_legions': {
            'text': "Легионы Проклятых - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'legion_heroes_d2'}, {'text': 'Страж Столицы', 'callback_data': 'unit_lgn_grdn_АшкаэльД2'}],
                [{'text': 'Воины', 'callback_data': 'legion_warriors_d2'}, {'text': 'Стрелки', 'callback_data': 'legion_archers_d2'}, {'text': 'Маги', 'callback_data': 'legion_mages_d2'}, {'text': 'Поддержка', 'callback_data': 'legion_support_d2'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_lgn_spcl_ИзвергД2'}, {'text': 'Призываемые существа', 'callback_data': 'legion_summoned_d2'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'legion_heroes_d1': {
            'text': "Герои Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Герцог', 'callback_data': 'unit_lgn_hero_ГерцогД1'}, {'text': 'Архидьявол', 'callback_data': 'unit_lgn_hero_АрхидьяволД1'}, {'text': 'Советник', 'callback_data': 'unit_lgn_hero_СоветникД1'}],
                [{'text': 'Баронесса', 'callback_data': 'unit_lgn_hero_БаронессаД1'}, {'text': 'Вор', 'callback_data': 'unit_lgn_hero_ВорЛегионовД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_heroes_d2': {
            'text': "Герои Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Герцог', 'callback_data': 'unit_lgn_hero_ГерцогД2'}, {'text': 'Архидьявол', 'callback_data': 'unit_lgn_hero_АрхидьяволД2'}, {'text': 'Советник', 'callback_data': 'unit_lgn_hero_СоветникД2'}],
                [{'text': 'Баронесса', 'callback_data': 'unit_lgn_hero_БаронессаД2'}, {'text': 'Вор', 'callback_data': 'unit_lgn_hero_ВорЛегионовД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'legion_warriors_d1': {
            'text': "Воины Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Одержимый', 'callback_data': 'unit_lgn_warr_ОдержимыйД1'}],
                [{'text': 'Берсерк', 'callback_data': 'unit_lgn_warr_БерсеркД1'}],
                [{'text': 'Антипаладин', 'callback_data': 'unit_lgn_warr_АнтипаладинД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_warriors_d2': {
            'text': "Воины Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Одержимый', 'callback_data': 'unit_lgn_warr_ОдержимыйД2'}],
                [{'text': 'Берсерк', 'callback_data': 'unit_lgn_warr_БерсеркД2'}],
                [{'text': 'Темный паладин', 'callback_data': 'unit_lgn_warr_ТемныйПаладинД2'}],
                [{'text': 'Рыцарь ада', 'callback_data': 'unit_lgn_warr_РыцарьАдаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'legion_mages_d1': {
            'text': "Маги Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Культист', 'callback_data': 'unit_lgn_mage_КультистД1'}],
                [{'text': 'Ведьма', 'callback_data': 'unit_lgn_mage_ВедьмаД1'}, {'text': '-', 'callback_data': 'legion_mages_d1'},{'text': 'Колдун', 'callback_data': 'unit_lgn_mage_КолдунД1'}],
                [{'text': 'Суккуб', 'callback_data': 'unit_lgn_mage_СуккубД1'}, {'text': '-', 'callback_data': 'legion_mages_d1'},{'text': 'Демонолог', 'callback_data': 'unit_lgn_mage_ДемонологД1'}],
                [{'text': '-', 'callback_data': 'legion_mages_d1'},{'text': 'Пандемониус', 'callback_data': 'unit_lgn_mage_ПандемониусД1'},{'text': 'Инкуб', 'callback_data': 'unit_lgn_mage_ИнкубД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_mages_d2': {
            'text': "Маги Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Сектант', 'callback_data': 'unit_lgn_mage_СектантД2'}],
                [{'text': 'Ведьма', 'callback_data': 'unit_lgn_mage_ВедьмаД2'},{'text': 'Чародей', 'callback_data': 'unit_lgn_mage_ЧародейД2'}],
                [{'text': 'Колдунья', 'callback_data': 'unit_lgn_mage_КолдуньяД2'},{'text': 'Демонолог', 'callback_data': 'unit_lgn_mage_ДемонологД2'},{'text': 'Доппельгангер', 'callback_data': 'unit_lgn_mage_ДоппельгангерД2'}],
                [{'text': 'Суккуб', 'callback_data': 'unit_lgn_mage_СуккубД2'},{'text': 'Пандемониус', 'callback_data': 'unit_lgn_mage_ПандемониусД2'},{'text': 'Инкуб', 'callback_data': 'unit_lgn_mage_ИнкубД2'}],
                [{'text': 'Модеус', 'callback_data': 'unit_lgn_mage_МодеусД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'legion_archers_d1': {
            'text': "Стрелки Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Горгулья', 'callback_data': 'unit_lgn_arch_ГоргульяД1'}],
                [{'text': 'Мраморная горгулья', 'callback_data': 'unit_lgn_arch_МраморнаяГоргульяД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_archers_d2': {
            'text': "Стрелки Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Горгулья', 'callback_data': 'unit_lgn_arch_ГоргульяД2'}],
                [{'text': 'Мраморная горгулья', 'callback_data': 'unit_lgn_arch_МраморнаяГоргульяД2'}],
                [{'text': 'Ониксовая горгулья', 'callback_data': 'unit_lgn_arch_ОниксоваяГоргульяД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'legion_support_d1': {
            'text': "Поддержка Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Дьявол', 'callback_data': 'unit_lgn_supp_ЧертД1'}],
                [{'text': 'Демон', 'callback_data': 'unit_lgn_supp_ДемонД1'}],
                [{'text': 'Молох', 'callback_data': 'unit_lgn_supp_МолохД1'}],
                [{'text': 'Чудовище', 'callback_data': 'unit_lgn_supp_ЧудовищеД1'},{'text': 'Повелитель демонов', 'callback_data': 'unit_lgn_supp_ПовелительДемоновД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_support_d2': {
            'text': "Поддержка Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Черт', 'callback_data': 'unit_lgn_supp_ЧертД2'}],
                [{'text': 'Демон', 'callback_data': 'unit_lgn_supp_ДемонД2'}],
                [{'text': 'Молох', 'callback_data': 'unit_lgn_supp_МолохД2'}],
                [{'text': 'Зверь', 'callback_data': 'unit_lgn_supp_ЗверьД2'},{'text': 'Повелитель демонов', 'callback_data': 'unit_lgn_supp_ПовелительДемоновД2'}],
                [{'text': 'Тиамат', 'callback_data': 'unit_lgn_supp_ТиаматД2'},{'text': 'Дьявол преисподней', 'callback_data': 'unit_lgn_supp_ДьяволПреисподнейД2'},{'text': 'Темный повелитель', 'callback_data': 'unit_lgn_supp_ТемныйПовелительД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'legion_summoned_d1': {
            'text': "Призываемые существа Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Адская гончья', 'callback_data': 'unit_lgn_smnd_АдскаяГончьяД1'}],
                [{'text': 'Белиарх', 'callback_data': 'unit_lgn_smnd_БелиархД1'}],
                [{'text': 'Мститель', 'callback_data': 'unit_lgn_smnd_МстительД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_legions'}]
            ]
        },
        'legion_summoned_d2': {
            'text': "Призываемые существа Легоинов Проклятых - выберите юнита:",
            'keyboard': [
                [{'text': 'Адская гончья', 'callback_data': 'unit_lgn_smnd_АдскаяГончьяД2'}],
                [{'text': 'Белиарх', 'callback_data': 'unit_lgn_smnd_БелиархД2'}],
                [{'text': 'Мститель', 'callback_data': 'unit_lgn_smnd_МстительД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_legions'}]
            ]
        },
        'sacred_undead': {
            'text': "Орды Нежити - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'undead_heroes_d1'}, {'text': 'Страж Столицы', 'callback_data': 'unit_und_grdn_АшганД1'}],
                [{'text': 'Воины', 'callback_data': 'undead_warriors_d1'}, {'text': 'Стрелки', 'callback_data': 'undead_archers_d1'}, {'text': 'Маги', 'callback_data': 'undead_mages_d1'}, {'text': 'Поддержка', 'callback_data': 'undead_support_d1'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_und_spcl_ОборотеньД1'}, {'text': 'Призываемые существа', 'callback_data': 'undead_summoned_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_units'}]
            ]
        },
        'd2_undead': {
            'text': "Орды Нежити - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'undead_heroes_d2'}, {'text': 'Страж Столицы', 'callback_data': 'unit_und_grdn_АшганД2'}],
                [{'text': 'Воины', 'callback_data': 'undead_warriors_d2'}, {'text': 'Стрелки', 'callback_data': 'undead_archers_d2'}, {'text': 'Маги', 'callback_data': 'undead_mages_d2'}, {'text': 'Поддержка', 'callback_data': 'undead_support_d2'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_und_spcl_ОборотеньД2'}, {'text': 'Призываемые существа', 'callback_data': 'undead_summoned_d2'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'undead_heroes_d1': {
            'text': "Герои Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Рыцарь смерти', 'callback_data': 'unit_und_hero_РыцарьСмертиД1'}, {'text': 'Королева личей', 'callback_data': 'unit_und_hero_КоролеваЛичейД1'}, {'text': 'Носферату', 'callback_data': 'unit_und_hero_НосфератуД1'}],
                [{'text': 'Баньши', 'callback_data': 'unit_und_hero_БаньшиД1'}, {'text': 'Вор', 'callback_data': 'unit_und_hero_ВорОрдД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_heroes_d2': {
            'text': "Герои Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Рыцарь смерти', 'callback_data': 'unit_und_hero_РыцарьСмертиД2'}, {'text': 'Королева личей', 'callback_data': 'unit_und_hero_КоролеваЛичейД2'}, {'text': 'Носферату', 'callback_data': 'unit_und_hero_НосфератуД2'}],
                [{'text': 'Баньши', 'callback_data': 'unit_und_hero_БаньшиД2'}, {'text': 'Вор', 'callback_data': 'unit_und_hero_ВорНежитиД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'undead_warriors_d1': {
            'text': "Воины Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Воитель', 'callback_data': 'unit_und_warr_ВоительД1'}],
                [{'text': 'Зомби', 'callback_data': 'unit_und_warr_ЗомбиД1'}, {'text': 'Тамплиер', 'callback_data': 'unit_und_warr_ТамплиерД1'}],
                [{'text': 'Воин-скелет', 'callback_data': 'unit_und_warr_ВоинСкелетД1'}, {'text': 'Темный лорд', 'callback_data': 'unit_und_warr_ТемныйЛордД1'}],
                [{'text': 'Скелет-чемпион', 'callback_data': 'unit_und_warr_СкелетЧемпионД1'},{'text': '-', 'callback_data': 'undead_warriors_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_warriors_d2': {
            'text': "Воины Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Воин', 'callback_data': 'unit_und_warr_ВоинНежитиД2'}],
                [{'text': 'Зомби', 'callback_data': 'unit_und_warr_ЗомбиД2'}, {'text': 'Храмовник', 'callback_data': 'unit_und_warr_ХрамовникД2'}],
                [{'text': 'Воин скелет', 'callback_data': 'unit_und_warr_ВоинСкелетД2'}, {'text': 'Лорд тьмы', 'callback_data': 'unit_und_warr_ЛордТьмыД2'}],
                [{'text': 'Скелет рыцарь', 'callback_data': 'unit_und_warr_РыцарьСкелетД2'}],
                [{'text': 'Воин призрак', 'callback_data': 'unit_und_warr_ВоинПризракД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'undead_mages_d1': {
            'text': "Маги Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Посвященный', 'callback_data': 'unit_und_mage_ПосвященныйД1'}],
                [{'text': 'Чернокнижник', 'callback_data': 'unit_und_mage_ЧернокнижникД1'}],
                [{'text': 'Некромант', 'callback_data': 'unit_und_mage_НекромантД1'},{'text': '-', 'callback_data': 'undead_mages_d1'},{'text': 'Дух', 'callback_data': 'unit_und_mage_ДухД1'}],
                [{'text': 'Лич', 'callback_data': 'unit_und_mage_ЛичД1'},{'text': 'Вампир', 'callback_data': 'unit_und_mage_ВампирД1'},{'text': '-', 'callback_data': 'undead_mages_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_mages_d2': {
            'text': "Маги Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Адепт', 'callback_data': 'unit_und_mage_АдептД2'}],
                [{'text': 'Чернокнижник', 'callback_data': 'unit_und_mage_ЧернокнижникД2'}],
                [{'text': 'Некромант', 'callback_data': 'unit_und_mage_НекромантД2'},{'text': 'Дух', 'callback_data': 'unit_und_mage_ДухД2'}],
                [{'text': 'Лич', 'callback_data': 'unit_und_mage_ЛичД2'},{'text': 'Вампир', 'callback_data': 'unit_und_mage_ВампирД2'},{'text': 'Тварь', 'callback_data': 'unit_und_mage_ТварьД2'},{'text': 'Смерть', 'callback_data': 'unit_und_mage_СмертьД2'}],
                [{'text': 'Архилич', 'callback_data': 'unit_und_mage_АрхиличД2'},{'text': 'Верховный вампир', 'callback_data': 'unit_und_mage_ВерховныйВампирД2'},{'text': '-', 'callback_data': 'undead_mages_d1'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'undead_archers_d1': {
            'text': "Стрелки Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Привидение', 'callback_data': 'unit_und_arch_ПривидениеД1'}],
                [{'text': 'Спектр', 'callback_data': 'unit_und_arch_СпектрД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_archers_d2': {
            'text': "Стрелки Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Привидение', 'callback_data': 'unit_und_arch_ПривидениеД2'}],
                [{'text': 'Призрак', 'callback_data': 'unit_und_arch_ПризракД2'}],
                [{'text': 'Тень', 'callback_data': 'unit_und_arch_ТеньД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'undead_support_d1': {
            'text': "Поддержка Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Виверна', 'callback_data': 'unit_und_supp_ВивернаД1'}],
                [{'text': 'Дракон Рока', 'callback_data': 'unit_und_supp_ДраконРокаД1'}],
                [{'text': 'Дракон смерти', 'callback_data': 'unit_und_supp_ДраконСмертиД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_support_d2': {
            'text': "Поддержка Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Виверна', 'callback_data': 'unit_und_supp_ВивернаД2'}],
                [{'text': 'Дракон Рока', 'callback_data': 'unit_und_supp_ДраконРокаД2'}],
                [{'text': 'Дракон смерти', 'callback_data': 'unit_und_supp_ДраконСмертиД2'}],
                [{'text': 'Драколич', 'callback_data': 'unit_und_supp_ДраколичД2'},{'text': 'Змей ужаса', 'callback_data': 'unit_und_supp_ЗмейУжасаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'undead_summoned_d1': {
            'text': "Призываемые существа Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Скелет', 'callback_data': 'unit_und_smnd_СкелетД1'}],
                [{'text': 'Гворн', 'callback_data': 'unit_und_smnd_ГворнД1'}],
                [{'text': 'Ночной кошмар', 'callback_data': 'unit_und_smnd_НочнойКошмарД1'}],
                [{'text': 'Смерть', 'callback_data': 'unit_und_smnd_СмертьД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_undead'}]
            ]
        },
        'undead_summoned_d2': {
            'text': "Призываемые существа Орд Нежити - выберите юнита:",
            'keyboard': [
                [{'text': 'Скелет', 'callback_data': 'unit_und_smnd_СкелетД2'}],
                [{'text': 'Гворн', 'callback_data': 'unit_und_smnd_ГворнД2'}],
                [{'text': 'Ночной кошмар', 'callback_data': 'unit_und_smnd_НочнойКошмарД2'}],
                [{'text': 'Танатос', 'callback_data': 'unit_und_smnd_ТанатосД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_undead'}]
            ]
        },
        'sacred_clans': {
            'text': "Горные Кланы - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'clans_heroes_d1'}, {'text': 'Страж Столицы', 'callback_data': 'unit_cln_grdn_ВитарД1'}],
                [{'text': 'Воины', 'callback_data': 'clans_warriors_d1'}, {'text': 'Стрелки', 'callback_data': 'clans_archers_d1'}, {'text': 'Маги', 'callback_data': 'clans_mages_d1'}, {'text': 'Поддержка', 'callback_data': 'clans_support_d1'}],
                [{'text': 'Особые существа', 'callback_data': 'clans_specials_d1'}, {'text': 'Призываемые существа', 'callback_data': 'clans_summoned_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_units'}]
            ]
        },
        'd2_clans': {
            'text': "Горные Кланы - выберите тип юнитов:",
            'keyboard': [
                [{'text': 'Герои', 'callback_data': 'clans_heroes_d2'}, {'text': 'Страж Столицы', 'callback_data': 'unit_cln_grdn_ВитарД2'}],
                [{'text': 'Воины', 'callback_data': 'clans_warriors_d2'}, {'text': 'Стрелки', 'callback_data': 'clans_archers_d2'}, {'text': 'Маги', 'callback_data': 'clans_mages_d2'}, {'text': 'Поддержка', 'callback_data': 'clans_support_d2'}],
                [{'text': 'Особые существа', 'callback_data': 'unit_cln_spcl_ЙетиД2'}, {'text': 'Призываемые существа', 'callback_data': 'clans_summoned_d2'}],
                [{'text': 'Назад', 'callback_data': 'd2_units'}]
            ]
        },
        'clans_heroes_d1': {
            'text': "Герои Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Королевский страж', 'callback_data': 'unit_cln_hero_КоролевскийСтражД1'}, {'text': 'Хранитель знаний', 'callback_data': 'unit_cln_hero_ХранительЗнанийД1'}, {'text': 'Инженер', 'callback_data': 'unit_cln_hero_ИнженерД1'}],
                [{'text': 'Гордый гном', 'callback_data': 'unit_cln_hero_ГордыйГномД1'}, {'text': 'Вор', 'callback_data': 'unit_cln_hero_ВорКлановД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_heroes_d2': {
            'text': "Герои Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Королевский страж', 'callback_data': 'unit_cln_hero_КоролевскийСтражД2'}, {'text': 'Хранитель знаний', 'callback_data': 'unit_cln_hero_ХранительЗнанийД2'}, {'text': 'Инженер', 'callback_data': 'unit_cln_hero_ИнженерД2'}],
                [{'text': 'Старейшина', 'callback_data': 'unit_cln_hero_СтарейшинаГномовД2'}, {'text': 'Вор', 'callback_data': 'unit_cln_hero_ВорГномовД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_warriors_d1': {
            'text': "Воины Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Гном', 'callback_data': 'unit_cln_warr_ГномД1'}],
                [{'text': 'Воин', 'callback_data': 'unit_cln_warr_ВоинД1'}],
                [{'text': 'Ветеран', 'callback_data': 'unit_cln_warr_ВетеранД1'}, {'text': '-', 'callback_data': 'clans_warriors_d1'},{'text': 'Горец', 'callback_data': 'unit_cln_warr_ГорецД1'}],
                [{'text': 'Почтенный воин', 'callback_data': 'unit_cln_warr_ПочтенныйВоинД1'}, {'text': 'Король гномов', 'callback_data': 'unit_cln_warr_КорольГномовД1'}, {'text': '-', 'callback_data': 'clans_warriors_d1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_warriors_d2': {
            'text': "Воины Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Гном', 'callback_data': 'unit_cln_warr_ГномД2'}],
                [{'text': 'Воин', 'callback_data': 'unit_cln_warr_ВоинД2'}],
                [{'text': 'Ветеран', 'callback_data': 'unit_cln_warr_ВетеранД2'},{'text': 'Горец', 'callback_data': 'unit_cln_warr_ГорецД2'}],
                [{'text': 'Старый ветеран', 'callback_data': 'unit_cln_warr_СтарыйВетеранД2'}, {'text': 'Отшельник', 'callback_data': 'unit_cln_warr_ОтшельникД2'}, {'text': 'Повелитель волков', 'callback_data': 'unit_cln_warr_ПовелительВолковД2'}],
                [{'text': 'Мастер рун', 'callback_data': 'unit_cln_warr_МастерРунД2'}, {'text': 'Король гномов', 'callback_data': 'unit_cln_warr_КорольГномовД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_mages_d1': {
            'text': "Маги Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Новичок', 'callback_data': 'unit_cln_mage_НовичокД1'}],
                [{'text': 'Послушник', 'callback_data': 'unit_cln_mage_ПослушникД1'}],
                [{'text': 'Алхимик', 'callback_data': 'unit_cln_mage_АлхимикД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_mages_d2': {
            'text': "Маги Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Травница', 'callback_data': 'unit_cln_mage_ТравницаД2'}],
                [{'text': 'Послушница', 'callback_data': 'unit_cln_mage_ПослушницаД2'}],
                [{'text': 'Друид', 'callback_data': 'unit_cln_mage_ДруидД2'},{'text': 'Алхимик', 'callback_data': 'unit_cln_mage_АлхимикД2'}],
                [{'text': 'Архидруид', 'callback_data': 'unit_cln_mage_АрхидруидД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_archers_d1': {
            'text': "Стрелки Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Метатель топоров', 'callback_data': 'unit_cln_arch_МетательТопоровД1'}],
                [{'text': 'Арбалетчик', 'callback_data': 'unit_cln_arch_АрбалетчикД1'}],
                [{'text': 'Огнеметчик', 'callback_data': 'unit_cln_arch_ОгнеметчикД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_archers_d2': {
            'text': "Стрелки Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Метатель топоров', 'callback_data': 'unit_cln_arch_МетательТопоровД2'}],
                [{'text': 'Арбалетчик', 'callback_data': 'unit_cln_arch_АрбалетчикД2'}],
                [{'text': 'Повелитель огня', 'callback_data': 'unit_cln_arch_ПовелительОгняД2'},{'text': 'Страж горна', 'callback_data': 'unit_cln_arch_СтражГорнаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_support_d1': {
            'text': "Поддержка Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Холмовой великан', 'callback_data': 'unit_cln_supp_ХолмовойВеликанД1'}],
                [{'text': 'Горный великан', 'callback_data': 'unit_cln_supp_ГорныйВеликанД1'}],
                [{'text': 'Ледяной великан', 'callback_data': 'unit_cln_supp_ЛедянойВеликанД1'},{'text': 'Грозовой великан', 'callback_data': 'unit_cln_supp_ГрозовойВеликанД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_support_d2': {
            'text': "Поддержка Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Холмовой великан', 'callback_data': 'unit_cln_supp_ХолмовойВеликанД2'}],
                [{'text': 'Горный великан', 'callback_data': 'unit_cln_supp_ГорныйВеликанД2'}],
                [{'text': 'Ледяной великан', 'callback_data': 'unit_cln_supp_ЛедянойВеликанД2'},{'text': 'Повелитель бури', 'callback_data': 'unit_cln_supp_ПовелительБуриД2'}],
                [{'text': 'Сын Имира', 'callback_data': 'unit_cln_supp_СынИмираД2'},{'text': 'Старейшина', 'callback_data': 'unit_cln_supp_СтарейшинаД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_summoned_d1': {
            'text': "Призываемые существа Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Рух', 'callback_data': 'unit_cln_smnd_РухД1'}],
                [{'text': 'Валькирия', 'callback_data': 'unit_cln_smnd_ВалькирияД1'}],
                [{'text': 'Каменный предок', 'callback_data': 'unit_cln_smnd_КаменныйПредокД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'clans_summoned_d2': {
            'text': "Призываемые существа Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Рух', 'callback_data': 'unit_cln_smnd_РухД2'}],
                [{'text': 'Валькирия', 'callback_data': 'unit_cln_smnd_ВалькирияД2'}],
                [{'text': 'Каменный предок', 'callback_data': 'unit_cln_smnd_КаменныйПредокД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_clans'}]
            ]
        },
        'clans_specials_d1': {
            'text': "Особые существа Горных Кланов - выберите юнита:",
            'keyboard': [
                [{'text': 'Медведь', 'callback_data': 'unit_cln_spcl_МедведьД1'}],
                [{'text': 'Йети', 'callback_data': 'unit_cln_spcl_ЙетиД1'}],
                [{'text': 'Назад', 'callback_data': 'sacred_clans'}]
            ]
        },
        'elves_specials_d2': {
            'text': "Особые существа Эльфийского Альянса - выберите юнита:",
            'keyboard': [
                [{'text': 'Грифон', 'callback_data': 'unit_elf_spcl_ГрифонД2'}],
                [{'text': 'Владыка небес', 'callback_data': 'unit_elf_spcl_ВладыкаНебесД2'}],
                [{'text': 'Назад', 'callback_data': 'd2_elves'}]
            ]
        }
    }
    return menus.get(callback_data)

def handle_file_download(chat_id, message_id, file_name, callback_data):
    """Обработка скачивания и отправки файла"""
    try:
        test = "0"
        file_url = search_dwld_info(file_name)
        test = "1"
        # Определяем клавиатуру для возврата
        if "dwld_mod_d1_" in callback_data:
            keyboard = get_menu_config('sacred_mods')['keyboard']
        #elif "dwld_mod_d1_" in callback_data:
        #    keyboard = get_menu_config('sacred_modes')['keyboard']
        else:
            return create_response(chat_id, "Ошибка", get_menu_config('main_menu')['keyboard'], message_id)
            #keyboard = get_menu_config('sacred_modes')['keyboard']
        test = "2"
        test = file_url.replace("amp;", "")
        response = requests.get(file_url.replace("amp;", ""), stream=True)
        response.raise_for_status()
        test = "3"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        test = "4"
        
        # Отправка файла через Telegram API
        telegram_url = f"https://api.telegram.org/bot1670400491:AAFDc5lIg5NEEpYBmNEcGQsCf7kR1T9ap64/sendDocument"
        
        with open(tmp_path, 'rb') as file:
            files = {'document': (file_name, file)}
            data = {'chat_id': chat_id, 'caption': 'Описание файла'}
            requests.post(telegram_url, files=files, data=data)
        test = "5"
        
        os.unlink(tmp_path)
        test = "6"
        
        return create_response(chat_id, "Файл отправлен!", get_menu_config('sacred_mods')['keyboard'], message_id)
        
    except Exception as e:
        print(f"File download error: {e}")
        return create_response(chat_id, f"Ошибка при загрузке файла {test}", get_menu_config('main_menu')['keyboard'], message_id)

def handle_unit_info(callback_data, chat_id, message_id):
    """Обработка информации о юнитах"""
    unit_name = callback_data[14:] 
    response_text = search_unit_info(unit_name)
    
    # Определяем клавиатуру для возврата
    if "emp_hero" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_heroes_d1')['keyboard']
    elif "emp_hero" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_heroes_d2')['keyboard']
    elif ("emp_grdn" in callback_data or "emp_spcl" in callback_data) and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_empire')['keyboard']
    elif ("emp_grdn" in callback_data or "emp_spcl" in callback_data) and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_empire')['keyboard']
    elif "emp_warr" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_warriors_d1')['keyboard']
    elif "emp_warr" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_warriors_d2')['keyboard']
    elif "emp_mage" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_mages_d1')['keyboard']
    elif "emp_mage" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_mages_d2')['keyboard']
    elif "emp_arch" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_archers_d1')['keyboard']
    elif "emp_arch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_archers_d2')['keyboard']
    elif "emp_supp" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_support_d1')['keyboard']
    elif "emp_supp" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_support_d2')['keyboard']
    elif "emp_smnd" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('empire_summoned_d1')['keyboard']
    elif "emp_smnd" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('empire_summoned_d2')['keyboard']
    elif "lgn_hero" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_heroes_d1')['keyboard']
    elif "lgn_hero" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('legion_heroes_d2')['keyboard']
    elif "lgn_warr" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_warriors_d1')['keyboard'] 
    elif "lgn_warr" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('legion_warriors_d2')['keyboard']
    elif "lgn_mage" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_mages_d1')['keyboard']
    elif "lgn_arch" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_archers_d1')['keyboard']
    elif "lgn_supp" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_support_d1')['keyboard']
    elif "lgn_smnd" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_summoned_d1')['keyboard']
    elif "lgn_mage" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('legion_mages_d2')['keyboard']
    elif "lgn_arch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('legion_archers_d2')['keyboard']
    elif "lgn_supp" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('legion_support_d2')['keyboard']
    elif "lgn_smnd" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('legion_summoned_d2')['keyboard']
    elif ("lgn_grdn" in callback_data or "lgn_spcl" in callback_data) and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_legions')['keyboard']
    elif ("lgn_grdn" in callback_data or "lgn_spcl" in callback_data) and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_legions')['keyboard']
    elif "und_hero" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_heroes_d1')['keyboard']
    elif "und_warr" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_warriors_d1')['keyboard']
    elif "und_mage" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_mages_d1')['keyboard']
    elif "und_arch" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_archers_d1')['keyboard']
    elif "und_supp" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_support_d1')['keyboard']
    elif "und_smnd" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('undead_summoned_d1')['keyboard']
    elif ("und_grdn" in callback_data or "und_spcl" in callback_data) and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_undead')['keyboard']
    elif ("und_grdn" in callback_data or "und_spcl" in callback_data) and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_undead')['keyboard']
    elif "und_hero" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_heroes_d2')['keyboard']
    elif "und_warr" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_warriors_d2')['keyboard']
    elif "und_mage" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_mages_d2')['keyboard']
    elif "und_arch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_archers_d2')['keyboard']
    elif "und_supp" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_support_d2')['keyboard']
    elif "und_smnd" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('undead_summoned_d2')['keyboard']
    elif "cln_hero" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_heroes_d1')['keyboard']
    elif "cln_warr" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_warriors_d1')['keyboard']
    elif "cln_mage" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_mages_d1')['keyboard']
    elif "cln_arch" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_archers_d1')['keyboard']
    elif "cln_supp" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_support_d1')['keyboard']
    elif "cln_smnd" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_summoned_d1')['keyboard']
    elif "cln_spcl" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('clans_specials_d1')['keyboard']
    elif "cln_grdn" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_clans')['keyboard']
    elif "cln_hero" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_heroes_d2')['keyboard']
    elif "cln_warr" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_warriors_d2')['keyboard']
    elif "cln_mage" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_mages_d2')['keyboard']
    elif "cln_arch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_archers_d2')['keyboard']
    elif "cln_supp" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_support_d2')['keyboard']
    elif "cln_smnd" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('clans_summoned_d2')['keyboard']
    elif "cln_spcl" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_clans')['keyboard']
    elif "elf_grdn" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_elves')['keyboard']
    elif "elf_hero" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_heroes_d2')['keyboard']
    elif "elf_warr" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_warriors_d2')['keyboard']
    elif "elf_mage" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_mages_d2')['keyboard']
    elif "elf_arch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_archers_d2')['keyboard']
    elif "elf_supp" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_support_d2')['keyboard']
    elif "elf_smnd" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_summoned_d2')['keyboard']
    elif "elf_spcl" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('elves_specials_d2')['keyboard']
    elif "elf_grdn" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_elves')['keyboard']
    elif "neu_humn" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_humans')['keyboard']
    elif "neu_elvs" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_elves')['keyboard']
    elif "neu_orcs" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_orcs')['keyboard']
    elif "neu_orcs" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_orcs')['keyboard']
    elif "neu_evil" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_evils')['keyboard']
    elif "neu_merf" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_merfolks')['keyboard']
    elif "neu_mrch" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_march')['keyboard']
    elif "neu_drgn" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_dragons')['keyboard']
    elif "neu_boss" in callback_data and unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_bosses')['keyboard']
    elif "neu_humn" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_humans')['keyboard']
    elif "neu_barb" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_barbarians')['keyboard']
    elif "neu_elvs" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_neutral_elves')['keyboard']
    elif "neu_dwrf" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_dwarfs')['keyboard']
    elif "neu_orcs" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_orcs')['keyboard']
    elif "neu_merf" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_merfolks')['keyboard']
    elif "neu_mrch" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_march')['keyboard']
    elif "neu_drgn" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_dragons')['keyboard']
    elif "neu_boss" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_bosses')['keyboard']
    elif "neu_drks" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_darkelves')['keyboard']
    elif "neu_unds" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_neutrals_undead')['keyboard']
    elif "neu_anml" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_animals')['keyboard']
    elif "neu_mnst" in callback_data and unit_name.endswith("Д2"):
        keyboard = get_menu_config('d2_monsters')['keyboard']
    elif unit_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_units')['keyboard']
    else:
        keyboard = get_menu_config('main_menu')['keyboard']
    
    return create_response(chat_id, response_text, keyboard, message_id)

def handle_item_info(callback_data, chat_id, message_id):
    """Обработка информации о предметах"""
    item_name = callback_data[10:] 
    response_text = search_item_info(item_name)
    
    # Определяем клавиатуру для возврата
    if "item_vals" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_values')['keyboard']
    elif "item_arts" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_artefacts')['keyboard']
    elif "item_toms" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_books')['keyboard']
    elif "item_bnrs" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_banners')['keyboard']
    elif item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_items')['keyboard']
    else:
        keyboard = get_menu_config('main_menu')['keyboard']
    
    return create_response(chat_id, response_text, keyboard, message_id)

def handle_spell_info(callback_data, chat_id, message_id):
    """Обработка информации о заклинаниях"""
    item_name = callback_data[10:] 
    response_text = search_item_info(item_name)
    
    # Определяем клавиатуру для возврата
    if "item_vals" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_values')['keyboard']
    elif "item_arts" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_artefacts')['keyboard']
    elif "item_toms" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_books')['keyboard']
    elif "item_bnrs" in callback_data and item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_banners')['keyboard']
    elif item_name.endswith("Д1"):
        keyboard = get_menu_config('sacred_items')['keyboard']
    else:
        keyboard = get_menu_config('main_menu')['keyboard']
    
    return create_response(chat_id, response_text, keyboard, message_id)

def search_item_info(search_text):
    """Поиск информации о юнитах в XML"""
    try:
        tree = ET.parse('ItemsInfo.xml')
        root = tree.getroot()
        
        for item in root:
            if item.tag.lower() == search_text.lower():
                return item.text.strip()
        
        return "Предмет не найден"
    except Exception as e:
        print(f"XML parse error: {e}")
        return search_text

def search_dwld_info(search_text):
    """Поиск ссылки на скачивание в XML"""
    try:
        tree = ET.parse('DownloadsInfo.xml')
        root = tree.getroot()
        
        for link in root:
            if link.tag.lower() == search_text.lower():
                return link.text.strip()
        
        return f"Ссылка {search_text} не найдена"
    except Exception as e:
        print(f"XML parse error: {e}")
        return search_text

def search_unit_info(search_text):
    """Поиск информации о юнитах в XML"""
    try:
        tree = ET.parse('UnitsInfo.xml')
        root = tree.getroot()
        
        for unit in root:
            if unit.tag.lower() == search_text.lower():
                return unit.text.strip()
        
        return "Юнит не найден"
    except Exception as e:
        print(f"XML parse error: {e}")
        return "Ошибка при загрузке данных"

def search_unit_info_in_chat(search_text):
    """Поиск информации о юнитах в XML"""
    try:
        tree = ET.parse('UnitsInfo.xml')
        root = tree.getroot()
        
        for unit in root:
            if unit.tag.lower() == search_text[6:].lower():
                return unit.text.strip()
        
        return "Юнит не найден"
    except Exception as e:
        print(f"XML parse error: {e}")
        return "Ошибка при загрузке данных"        

def create_response(chat_id, text, keyboard=None, message_id=None, reply_to_message_id=None):
    """Создание стандартного ответа"""
    response_data = {
        'method': 'editMessageText' if message_id else 'sendMessage',
        'chat_id': chat_id,
        'text': text
    }
    
    if message_id:
        response_data['message_id'] = message_id
    
    if reply_to_message_id:
        response_data['reply_to_message_id'] = reply_to_message_id
    
    if keyboard:
        response_data['reply_markup'] = {'inline_keyboard': keyboard}
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response_data),
        'isBase64Encoded': False
    }
