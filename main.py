import json
import sys
import requests
import settings
from datetime import datetime
from tqdm import tqdm


class PhotoFromVK:
    """  Класс, описывающий получение фотографий из 'Вконтакте'  """

    URL = "https://api.vk.com/method/photos.get"

    def __init__(self, token, user_id_vk, album_vk="profile", count_photos_vk=5):
        try:
            if album_vk != "profile" and album_vk != "wall":
                raise ValueError("Album может быть только profile или wall.")
            if not isinstance(count_photos_vk, int):
                raise ValueError("Count_photos_vk может быть только числом.")
            self.token = token
            self.user_id = user_id_vk
            self.album = album_vk
            self.count_photos = count_photos_vk
        except ValueError as er:
            print(er)
            sys.exit()

    def __get_common_params(self):
        return {
            "access_token": self.token,
            "v": "5.199"
        }

    def __get_photos(self):
        """Функция получает из 'Вконтакта' данные о фотографиях."""
        try:
            params = self.__get_common_params()
            params.update({"owner_id": self.user_id, "album_id": self.album,
                           "extended": 1, "photo_sizes": 1})
            response = requests.get(self.URL, params=params)
            info_photos_from_vk = response.json()
            response.raise_for_status()
            print(response.json())
            if "error" in info_photos_from_vk:
                raise ValueError(f"Ошибка в получении данных из 'Вконтакте',"
                                 f" нужно проверить входные данные.")
        except ValueError as e:
            print(e)
        except requests.exceptions.HTTPError as e:
            print(f"Произошла ошибка при получении данных из 'Вконтактe'!!! {e}")
        except Exception as e:
            print(f"Произошла ошибка при получении данных из 'Вконтактe'!!! {e}")
        else:
            return info_photos_from_vk

    def __get_url_photo_max_size(self, list_sizes):
        """
        Функция определяет фотографию наибольшего размера.
        :param list_sizes: Список, состоящий из словарей (фотографий разного размера)
        :return: Кортеж из url и type фотографии наибольшего размера
        """
        for type_size in ["w", "z", "y", "x", "r", "q", "p", "o", "m", "s"]:
            for size in list_sizes:
                if size["type"] == type_size:
                    return size["url"], size["type"]
        print("Ошибка в данных о фотографии. Нет нужного значения type.")
        sys.exit()

    def __get_count_photos(self):
        """Функция получает общее количество фотографий."""
        total_photos = self.__get_photos()["response"]["count"]
        return total_photos

    def __get_data(self):
        """
        Функция обрабатывает полученные данные из VK с учётом лимита по количеству фотографий.
        :return: Список словарей. Словарь содержит кол-во лайков, форматированную дату, ссылку, тип наиб.фото.
        """
        info_photos_from_vk = self.__get_photos()
        if info_photos_from_vk["response"]["count"] == 0:
            print(f"Вконтакте по данному user_id: {self.user_id} нет фотографий.")
            sys.exit()
        if self.count_photos > info_photos_from_vk["response"]["count"]:
            print(f"Вконтакте по user_id: {self.user_id} можно загрузить только"
                  f" {self.__get_count_photos()} фотографии")
            sys.exit()
        try:
            info_photos_limit_count = []
            count = 0
            for item in info_photos_from_vk["response"]["items"]:
                count_likes = item["likes"]["count"]
                format_date = datetime.utcfromtimestamp(item["date"]).strftime("%d-%m-%Y-%H_%M_%S")
                url_photo, type_size = self.__get_url_photo_max_size(item["sizes"])
                dict_data = {"count_likes": count_likes, "format_date": format_date,
                             "url_photo": url_photo, "type": type_size}
                info_photos_limit_count.append(dict_data)
                count += 1
                if count == self.count_photos:
                    return info_photos_limit_count
        except Exception as exp:
            print(f"Произошла ошибка в get_data()!!! {exp}")

    def get_info_photos_for_yandex(self):
        """
        Функция формирует имя фотографии и удаляет лишние данные.
        :return: Список словарей.
        """
        try:
            info_photos_for_yandex = self.__get_data()
            list_likes = []
            for info_photo in tqdm(info_photos_for_yandex, desc="Идёт обработка фотографий... ", unit=" фото"):
                if info_photo["count_likes"] not in list_likes:
                    list_likes.append(info_photo["count_likes"])
                    info_photo["file_name"] = str(info_photo["count_likes"])
                    del info_photo["count_likes"]
                    del info_photo["format_date"]
                else:
                    info_photo["file_name"] = str(info_photo["count_likes"]) + '_' + info_photo["format_date"]
                    del info_photo["count_likes"]
                    del info_photo["format_date"]
            return info_photos_for_yandex
        except Exception as exc:
            print(f"Произошла ошибка в get_info_photos_for_yandex!!! {exc}")

    def get_json_file(self):
        """Функция удаляет данные по url и сохраняет данные в json-файл."""
        try:
            info_photos_updated = self.get_info_photos_for_yandex()
            for item in info_photos_updated:
                del item["url_photo"]
            with open("result.json", "w") as write_file:
                json.dump(info_photos_updated, write_file)
        except Exception as ex_n:
            print(f"Ошибка!!! {ex_n}")


class PhotoInYandex:
    """ Класс, описывающий загрузку фотографий на компьютер и с компьютера на ЯндексДиск"""

    URL_CREATE_FOLDER = "https://cloud-api.yandex.net/v1/disk/resources"
    URL_UPLOAD_LINK = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    NAME_FOLDER_COMPUTER = "images"  # должна быть создана вручную на компьютере

    def __init__(self, token, info_photos):
        try:
            if not isinstance(info_photos, list) or token == "":
                raise ValueError("info_photos должен быть списком")
            for info_photo in info_photos:
                if ("url_photo" and "file_name") not in info_photo:
                    raise ValueError("Некорректные данные в info_photos.")
            self.token_ya = token
            self.info_photos = info_photos
            self.headers = {
                "Authorization": f"OAuth {token}"
            }
        except ValueError as ex_5:
            print(ex_5)
            sys.exit()

    def __create_folder(self, name_folder_yandex):
        """Функция создаёт новую папку на ЯндексДиски."""
        params = {
            "path": f"/{name_folder_yandex}"
        }
        try:
            response = requests.put(self.URL_CREATE_FOLDER, params=params, headers=self.headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Произошла ошибка при создании папки!!! {e}.")
        except Exception as e:
            print(f"ОШИБКА при создании папки!!! {e}")

    def __download_photo_on_computer(self):
        """Функция скачивает фотографии по url на компьютер."""
        try:
            for item in tqdm(self.info_photos, desc="Идёт загрузка фотографий на компьютер", unit=" файл"):
                filename = item["file_name"]
                url_photo = item["url_photo"]
                response = requests.get(url_photo)
                response.raise_for_status()
                with open(f"{self.NAME_FOLDER_COMPUTER}/{filename}", "wb") as file:
                    file.write(response.content)
        except requests.exceptions.HTTPError as e:
            print(f"Произошла ошибка при скачивании фотографий на компьютер!!!! {e}")
        except FileNotFoundError as e:
            print(f"Произошла ошибка при скачивании фотографий на компьютере! {e}.")
        except Exception as e:
            print(f"Произошла ошибка при скачивании фотографий на компьютер! {e}")

    def download_photo_on_yandex(self, name_folder_yandex):
        """Функция загружает фотографии в созданную папку на ЯндексДиск."""
        self.__create_folder(name_folder_yandex)
        self.__download_photo_on_computer()
        try:
            for item in tqdm(self.info_photos, desc="Идёт загрузка фотографий на яндекс", unit=" файл"):
                filename = item["file_name"]
                params = {
                    "path": f"/{name_folder_yandex}/{filename}"
                }

                #  получаем ссылки для загрузки фотографий на ЯндексДиск
                response = requests.get(self.URL_UPLOAD_LINK, params=params, headers=self.headers)
                response.raise_for_status()
                upload_link = response.json()['href']
                if response.status_code == 200:
                    print("Ссылка для загрузки на ЯндексДиск получена.")

                # загружаем фотографии на ЯндексДиск
                with open(fr"{self.NAME_FOLDER_COMPUTER}\{filename}", "rb") as file:
                    response_download = requests.put(upload_link, files={"file": file})
                    if response_download.status_code == 201:
                        print(f"Фотография '{filename}' загружена на ЯндексДиск.")
        except requests.exceptions.HTTPError as e:
            print(f"Произошла ошибка при загрузки фотографий на ЯндексДиск!!! {e}")
        except FileNotFoundError as e:
            print(f"Произошла ошибка при загрузки фотографий на ЯндексДиск! {e}")
        except Exception as e:
            print(f"ОШИБКА при загрузки фотографий на ЯндексДиск!!! {e}")


if __name__ == '__main__':

    try:
        user_id = int(input("Введите id VK: "))
        if not isinstance(user_id, int):
            raise ValueError
        token_ya = input("Введите токен ЯндексДиска: ")
        if token_ya == "":
            raise ValueError("токен должен быть строкой.")

        photo_from_vk = PhotoFromVK(token=settings.ACCESS_TOKEN, user_id_vk=user_id,
                                    album_vk="wall", count_photos_vk=20)
        photo_from_vk.get_json_file()
        data_for_ya = photo_from_vk.get_info_photos_for_yandex()
        photo_in_ya = PhotoInYandex(token=token_ya, info_photos=data_for_ya)
        photo_in_ya.download_photo_on_yandex(name_folder_yandex="Image")
    except ValueError as ex:
        print(f"Введите корректные данные: {ex}")
