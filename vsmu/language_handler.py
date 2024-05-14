import json
import configparser

import vsmu.path_handler as pathhandler

DEFAULT_LANG: str = 'en_US'

class LanguageHandler:
    def __init__(self, args_language=DEFAULT_LANG):
        # On vérifie si args.language existe
        if args_language:
            self.lang = f'{args_language}.json'
        # Sinon on récupère la langue via config.ini
        else:
            try:
                # Si on définit manuellement la langue via le fichier config
                self.config_read = configparser.ConfigParser(allow_no_value=True, interpolation=None)
                self.config_read.read(pathhandler.get_configfile_path(), encoding='utf-8-sig')
                self.config_lang = self.config_read.get('Language', 'language')
                self.lang = f'{self.config_lang}.json'
            # On charge le fichier en_US.json
            except (configparser.NoOptionError, configparser.NoSectionError):
                self.lang = f'{DEFAULT_LANG}.json'
        pathhandler.set_current_lang_file_path(self.lang)

        # On charge le fichier de langue
        lang_json = open(pathhandler.get_current_lang_file_path(), 'r', encoding='utf-8-sig')
        self.i18n = json.load(lang_json)
        lang_json.close()

    def get_default(self, key: str) -> str:
        pathhandler.set_current_lang_file_path(f'{DEFAULT_LANG}.json')
        lang_json = open(pathhandler.get_current_lang_file_path(), 'r', encoding='utf-8-sig')
        i18n = json.load(lang_json)
        lang_json.close()
        pathhandler.set_current_lang_file_path(self.lang)
        return i18n[key]

    def get(self, key: str) -> str:
        if key in list(self.i18n[key]):
            return self.i18n[key]
        return self.get_default(key)

    # On crée une tuple pour les réponses O/N
    def yesno(self, i: int = -1) -> str or tuple[str]:
        opt = (
            self.get('yes').lower(),
            self.get('no').lower(),
            self.get('yes')[0].lower(),
            self.get('no')[0].lower()
        )
        if i == -1:
            return opt
        else:
            return opt[i]

    # Dico pour les langues - Region, langue-abr, langue, index
    @staticmethod
    def supported_languages() -> dict:
        return {
            "DE": ["de", "Deutsch", '1'],
            "US": ["en", "English", '2'],
            "ES": ["es", "Español", '3'],
            "FR": ["fr", "Français", '4'],
            "IT": ["it", "Italiano", '5'],
            "BR": ["pt", "Português", '6'],
            "RU": ["ru", "Русский", '7'],
            "UA": ["uk", "Українська", '8']
        }