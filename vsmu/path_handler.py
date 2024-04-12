import os
from pathlib import Path
import platform
from shutil import rmtree

# Mods path that is the default for system
current_os = platform.system()
mods_path = None
config_file_path = None
lang_file_path = None


def get_default_mods_path():
    # On vérifie si le chemin contient des variables d'environnement
    # On vérifie si la variable %appdata% (ou HOME) est dans le chemin et on la remplace par la variable systeme.
    if current_os == 'Windows':
        # On cherche les versions installées de Vintage Story
        return Path(os.getenv('appdata'), 'VintagestoryData', 'Mods')
    elif current_os == 'Linux':
        return Path(Path.home(), '.config', 'VintagestoryData', 'Mods')

    return None


# On récupère l'argument modspath
def get_mods_path():
    global mods_path

    system_mods_path = get_default_mods_path()

    if mods_path is not None and Path(mods_path).is_dir():
        return Path(mods_path)
    elif system_mods_path is not None and system_mods_path.is_dir():
        return system_mods_path

    return None


def get_config_path():
    # On cherche les versions installées de Vintage Story
    if current_os == 'Windows':
        config_path = Path(os.getenv('appdata'), 'VS_ModsUpdater')
    elif current_os == 'Linux':
        config_path = Path(Path.home(), '.config', 'VS_ModsUpdater')
    else:
        config_path = None

    if config_path is None:
        raise Exception('OS not supported')

    if not config_path.is_dir():
        os.mkdir(config_path)

    return config_path


def get_configfile_path():
    global config_file_path

    if config_file_path.is_file() and os.stat(config_file_path).st_size == 0:
        os.remove(config_file_path)
    return config_file_path


def get_logs_path():
    log_path = Path(get_config_path(), 'logs')

    if not log_path.is_dir():
        os.mkdir(log_path)

    return Path(log_path)


def get_temp_path():
    temp_path = Path(get_config_path(), 'temp')

    if not temp_path.is_dir():
        os.mkdir(temp_path)

    return Path(temp_path)


def get_lang_path():
    return Path(Path.cwd(), 'lang')


# On efface le dossier temp
def clear_temp_folder():
    if get_temp_path().is_dir():
        rmtree(get_temp_path())


def set_current_mods_path(path: Path):
    global mods_path

    mods_path = path


def get_current_mods_path():
    global mods_path

    if mods_path is None:
        mods_path = get_default_mods_path()

    if not mods_path.is_dir():
        raise Exception('No mods path defined')

    return mods_path


def set_current_config_file_path(path: Path):
    global config_file_path

    config_file_path = path


def get_current_config_file_path():
    global config_file_path

    if config_file_path is None:
        config_file_path = Path(get_config_path(), 'config.ini')

    if not config_file_path.is_file():
        print(config_file_path)
        raise OSError("Config file doesn't exist")

    return config_file_path


def get_mods_table_csv_path():
    return Path(get_temp_path(), 'csvtemp.csv')


def get_default_lang_file_path():
    if not Path(get_lang_path(), 'en_US.json').is_file():
        raise OSError('Default language file doesn\'t exist')
    return Path(get_lang_path(), 'en_US.json')

def get_current_lang_file_path():
    global lang_file_path

    if lang_file_path is None or not lang_file_path.is_file():
        lang_file_path = Path(get_lang_path(), 'en_US.json')

    return lang_file_path


def set_current_lang_file_path(lang: str):
    global lang_file_path

    lang_file_path = Path(get_lang_path(), lang)
