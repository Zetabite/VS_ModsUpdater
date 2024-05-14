#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vintage Story mod management:
- Lists installed mods, checks for newer versions and downloads them
- Displays summary
- Creates an updates.log file
- You can limit the game version for mod updates
- Check for ModsUpdater updates on moddb
- Windows + Linux
- script execution by command line for servers.
- Possibility of generating a pdf file of the mod list
"""

__author__ = ["Laerinok", "Zetabite"]
__date__ = "2024-04-12"
__version__ = "2.0.0"

import argparse
import configparser
import csv
import glob
import os
import platform
import re
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

import requests
import semver
import wget
from bs4 import BeautifulSoup
from fpdf import FPDF, YPos, XPos
from rich.prompt import Prompt
from rich import print as rprint
import logging

import vsmu.path_handler as paths
from vsmu.language_handler import LanguageHandler

# On récupère le system
current_os = platform.system()

mods_url = "https://mods.vintagestory.at"
api_url = f"{mods_url}/api/mod"
show_url = f"{mods_url}/show/mod"

lang_handler = LanguageHandler("en_US")
logger = logging.getLogger("VS_ModsUpdater")


def log_info(rprint_msg: str = "", logger_msg: str = "", args: list = []) -> None:
    args: list[str] = [str(a) for a in args]
    rprint(rprint_msg % tuple(args))
    logger.info(logger_msg, *args)


def log_warning(rprint_msg: str = "", logger_msg: str = "", args: list = []) -> None:
    args: list[str] = [str(a) for a in args]
    rprint(rprint_msg % tuple(args))
    logger.warning(logger_msg, *args)


def log_error(rprint_msg: str = "", logger_msg: str = "", args: list = []) -> None:
    args: list[str] = [str(a) for a in args]

    rprint(
        ("[red]%s[/red]\n" % lang_handler.get("error_msg")) + (rprint_msg % tuple(args))
    )
    logger.error(logger_msg, *args, exc_info=1)


def log_debug(rprint_msg: str = "", logger_msg: str = "", args: list = []) -> None:
    args: list[str] = [str(a) for a in args]
    rprint(rprint_msg % tuple(args))
    logger.debug(logger_msg, *args)


class VSUpdate:
    def __init__(self):
        # Définition des chemins
        self.lang_name = ""

        # On crée le fichier config.ini si inexistant,
        # puis (si lancement du script via l"executable et non
        # en ligne de commande) on sort du programme si on veut ajouter des mods à exclure
        if (
            paths.get_configfile_path() is None
            or not paths.get_configfile_path().is_file()
        ):
            if args.nopause == "false":
                log_info(
                    "\n\t\t[bold cyan]%s[/bold cyan]\n",
                    "%s",
                    [lang_handler.get("first_launch_title")],
                )
                i = 1

                for _, item in lang_handler.supported_languages().items():
                    rprint(f"\t\t - {i}) {item[1]}, {item[0]}")
                    i += 1
                lang_choice_result = Prompt.ask(
                    f"\n\t\t[bold cyan]{lang_handler.get('first_launch_lang_choice')}[/bold cyan]",
                    choices=[str(i) for i in range(1, 9)],
                    show_choices=False,
                    default="2",
                )

                for region, lang_ext in lang_handler.supported_languages().items():
                    if lang_choice_result == lang_ext[2]:
                        paths.set_current_lang_file_path(f"{lang_ext[0]}_{region}.json")
                        self.lang_name = lang_ext[1]
            elif args.language:
                paths.set_current_lang_file_path(f"{args.language}.json")

                for region, lang_ext in lang_handler.supported_languages().items():
                    # On récupere le nom de la langue
                    if region == args.language.split("_")[1]:
                        self.lang_name = lang_ext[1]
            else:
                paths.set_current_lang_file_path("en_US.json")
                self.lang_name = "English"

            # On crée le fichier config.ini
            self.set_config_ini()
            # On récupère les valeurs de config.ini
            self.config_read = configparser.ConfigParser(
                allow_no_value=True, interpolation=None
            )
            self.config_read.read(paths.get_configfile_path(), encoding="utf-8-sig")
            self.force_update = self.config_read.get(
                "ModsUpdater", "force_update"
            )  # On récupère la valeur de force_update
            self.disable_mod_dev = self.config_read.get(
                "ModsUpdater", "disable_mod_dev"
            )  # On récupère l"option pour la maj ou non des version dev des mod.
            log_info(
                "\n\t[bold cyan]%s[/bold cyan]:",
                "%s",
                [lang_handler.get("first_launch_config_done")],
            )
            log_info(
                "\t\t- [bold cyan]%s[/bold cyan]: %s",
                "%s: %s",
                [lang_handler.get("first_launch_lang_txt"), self.lang_name],
            )
            log_info(
                "\t\t- [bold cyan]%s: %s[/bold cyan]",
                "%s: %s",
                [lang_handler.get("first_launch_pathmods"), paths.get_mods_path()],
            )
            log_info(
                "\t\t- [bold cyan]%s[/bold cyan]:",
                "%s",
                [lang_handler.get("first_launch_game_ver_max")],
            )
            log_info(
                "\t\t- [bold cyan]%s: %s[/bold cyan]:",
                "%s: %s",
                ["force_update", self.force_update],
            )
            log_info(
                "\t\t- [bold cyan]%s: %s[/bold cyan]:",
                "%s: %s",
                ["disable_mod_dev", self.disable_mod_dev],
            )

            # On demande de continuer ou on quitte
            if args.nopause == "false":
                log_info(
                    "\n\t[bold cyan]%s[/bold cyan]",
                    "%s",
                    [lang_handler.get("first_launch2")],
                )
                maj_ok = Prompt.ask(
                    f"\n\t{lang_handler.get('first_launch3')}",
                    choices=lang_handler.yesno(),
                )

                if maj_ok == lang_handler.yesno(1) or maj_ok == lang_handler.yesno(3):
                    log_info("%s", "%s", [lang_handler.get("end_of_prg")])

                    if paths.get_temp_path().is_dir():
                        shutil.rmtree(paths.get_temp_path())
                    sys.exit()

        # On charge le fichier config.ini
        self.config_read = configparser.ConfigParser(
            allow_no_value=True, interpolation=None
        )
        self.config_read.read(paths.get_configfile_path(), encoding="utf-8-sig")
        # Définition des listes
        self.mod_filename = []
        self.mod_name_list = []
        self.mods_exclu = []
        self.non_mods_zipfile = []
        # Mods_list
        self.liste_mod_maj_filename = []
        # Définition des dico
        self.mods_updated = {}
        # Définition des variables
        self.modename = None
        self.nb_maj = 0
        self.gamever_limit = self.config_read.get(
            "Game_Version_max", "version"
        )  # On récupère la version max du jeu pour la maj

        if args.forceupdate:  # On récupère la valeur de force_update
            self.force_update = args.forceupdate
        else:
            self.force_update = self.config_read.get("ModsUpdater", "force_update")

        if args.disable_mod_dev:
            self.disable_mod_dev = args.disable_mod_dev
        else:
            self.disable_mod_dev = self.config_read.get(
                "ModsUpdater", "disable_mod_dev"
            )
        self.modinfo_content = None
        self.version_locale = ""
        self.mod_last_version_online = ""
        self.user_language = ""
        # variables json_correction
        self.name_json = ""
        self.version_json = ""
        self.modid_json = ""
        self.moddesc_json = ""
        self.regex_name_json = ""
        self.result_name_json = ""
        self.regex_version_json = ""
        self.result_version_json = ""
        self.regex_modid_json = ""
        self.result_modid_json = ""
        self.regex_moddesc_json = ""
        self.result_moddesc_json = ""
        # variables extract_modinfo
        self.filepath = ""
        # Accueil
        self.version = ""
        # Update_mods
        self.Path_Changelog = ""
        # config_file
        self.exclusion_size = None

    def set_config_ini(self):
        # Création du config.ini si inexistant
        # Ajout du contenu
        config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
        mu_ver = __version__
        config.add_section("ModsUpdater")
        config.set("ModsUpdater", "# Info about the creation of the config.ini file")
        config.set("ModsUpdater", "ver", mu_ver)
        config.set(
            "ModsUpdater",
            "# Enable or disable Force_Update for every mods. If enabled, it will download the last version for ALL mods, even if the version is already the latest. (true/false default=false)",
        )
        config.set("ModsUpdater", "force_update", "false")
        config.set(
            "ModsUpdater",
            "# Allow to disable or enable update of mod in dev or prerelease (true/false default=false).",
        )
        config.set("ModsUpdater", "disable_mod_dev", "false")
        config.add_section("ModPath")
        config.set("ModPath", "path", str(paths.get_mods_path()))
        config.add_section("Language")
        config.set("Language", lang_handler.get("language"))

        #  Si l"argument lang a été transmis
        if args.language:
            config.set("Language", "language", args.language)  # from command line
        else:
            regex_lang = r"\/[a-z]{1,2}_[A-Z]{1,2}\.json$"
            result_lang = re.search(regex_lang, str(paths.get_current_lang_file_path()))
            config.set("Language", "language", result_lang[1])
        config.add_section("Game_Version_max")
        config.set("Game_Version_max", lang_handler.get("setconfig01"))
        config.set("Game_Version_max", "version", "100.0.0")
        config.add_section("Mod_Exclusion")
        config.set("Mod_Exclusion", lang_handler.get("setconfig"))

        if args.exclusion:
            for i in range(0, len(args.exclusion)):
                config.set("Mod_Exclusion", f"mod{i + 1}", args.exclusion[i])
        else:
            for i in range(1, 11):
                config.set("Mod_Exclusion", f"mod{i}", "")
        with open(paths.get_configfile_path(), "w", encoding="utf-8") as cfgfile:
            config.write(cfgfile)

    def json_correction(self, txt_json):
        self.regex_name_json = r'"{0,1}name"{0,1} {0,}: {0,}"(.*)",{0,}'
        self.result_name_json = re.search(
            self.regex_name_json, txt_json, flags=re.IGNORECASE
        )
        self.regex_version_json = r'"{0,1}version"{0,1} {0,}: {0,}"(.*)",{0,}'
        self.result_version_json = re.search(
            self.regex_version_json, txt_json, flags=re.IGNORECASE
        )
        self.regex_modid_json = r'"{0,1}modid"{0,1} {0,}: {0,}"(.*)",{0,}'
        self.result_modid_json = re.search(
            self.regex_modid_json, txt_json, flags=re.IGNORECASE
        )
        self.regex_moddesc_json = '"{0,1}description"{0,1} {0,}: {0,}"(.*)",{0,}'
        self.result_moddesc_json = re.search(
            self.regex_moddesc_json, txt_json, flags=re.IGNORECASE
        )

        if self.result_name_json:
            self.name_json = self.result_name_json.group(2)

        if self.result_version_json:
            self.version_json = self.result_version_json.group(2)

        if self.result_modid_json:
            self.modid_json = self.result_modid_json.group(2)

        if self.result_moddesc_json:
            self.moddesc_json = self.result_moddesc_json.group(2)
        log_info(
            "self.name_json: %s\nself.version_json: %s\nself.modid_json: %s\nself.moddesc_json: %s",
            "self.name_json: %s\nself.version_json: %s\nself.modid_json: %s\nself.moddesc_json: %s",
            [self.name_json, self.version_json, self.modid_json, self.moddesc_json],
        )

        return self.name_json, self.version_json, self.modid_json, self.moddesc_json

    def extract_modinfo(self, file):
        # On trie les fichiers .zip et .cs
        type_file = Path(file).suffix
        if type_file == ".zip":
            # On lit le fichier modinfo.json de l"archive et on recupere le modid, name et version
            self.filepath = Path(paths.get_mods_path(), file)

            if zipfile.is_zipfile(
                self.filepath
            ):  # Vérifie si fichier est un Zip valide
                with zipfile.ZipFile(self.filepath) as fichier_zip:
                    with fichier_zip.open("modinfo.json") as modinfo_json:
                        self.modinfo_content = modinfo_json.read().decode("utf-8-sig")

            try:
                regex_name = r'"{0,1}name"{0,1} {0,}: {0,}"(.*)",{0,}'
                result_name = re.search(
                    regex_name, self.modinfo_content, flags=re.IGNORECASE
                )
                regex_modid = r'"{0,1}modid"{0,1} {0,}: {0,}"(.*)",{0,}'
                result_modid = re.search(
                    regex_modid, self.modinfo_content, flags=re.IGNORECASE
                )
                regex_version = r'"{0,1}version"{0,1} {0,}: {0,}"(.*)",{0,}'
                result_version = re.search(
                    regex_version, self.modinfo_content, flags=re.IGNORECASE
                )
                regex_description = r'"{0,1}description"{0,1} {0,}: {0,}"(.*)",{0,}'
                result_description = re.search(
                    regex_description, self.modinfo_content, flags=re.IGNORECASE
                )
                mod_name = result_name.group(1)

                if result_modid is not None:
                    mod_modid = result_modid.group(1)
                else:
                    mod_modid = mod_name.replace(" ", "").lower()
                mod_version = result_version.group(1)

                if result_description is not None:
                    mod_description = result_description.group(1)
                else:
                    mod_description = ""
            except Exception:
                try:
                    json_correct = self.json_correction(self.modinfo_content)
                    mod_name = json_correct[0]
                    mod_version = json_correct[1]
                    mod_modid = json_correct[2]

                    if json_correct[3] is not None:
                        mod_description = json_correct[3]
                    else:
                        mod_description = ""
                except Exception:
                    log_error("%s:", "%s:", [file])
                log_error("%s:", "%s:", [file])
        elif type_file == ".cs":
            self.filepath = Path(paths.get_mods_path(), file)

            with open(self.filepath, "r", encoding="utf-8-sig") as fichier_cs:
                cs_file = fichier_cs.read()
                regexp_name = "(namespace )(\\w*)"
                result_name = re.search(regexp_name, cs_file, flags=re.IGNORECASE)
                regexp_version = '(Version\\s=\\s")([\\d.]*)"'
                result_version = re.search(regexp_version, cs_file, flags=re.IGNORECASE)
                regexp_description = 'Description = "(.*)",'
                result_description = re.search(
                    regexp_description, cs_file, flags=re.IGNORECASE
                )
                mod_name = result_name[2]
                mod_version = result_version[2]
                mod_modid = mod_name
                mod_description = result_description[1]
        return mod_name, mod_modid, mod_version, mod_description, self.filepath

    def liste_complete_mods(self):
        # On crée la liste contenant les noms des fichiers zip des mods
        for elem in paths.get_mods_path().glob("*.zip"):
            mod_zipfile = zipfile.ZipFile(elem, "r")

            try:  # On ajoute uniquement les fichiers zip qui sont des mods
                zipfile.ZipFile.getinfo(mod_zipfile, "modinfo.json")
                self.mod_filename.append(elem.name)
            except KeyError:
                pass
        # On ajoute les fichiers .cs
        for elem_cs in paths.get_mods_path().glob("*.cs"):
            self.mod_filename.append(elem_cs.name)

        if len(self.mod_filename) == 0:
            log_info("%s", "%s", [lang_handler.get("err_list")])
            os.system("pause")
            sys.exit()
        return self.mod_filename

    @staticmethod
    def verif_formatversion(v1, v2):
        new_ver1 = []
        new_ver2 = []
        ver1 = v1.split(".")
        for elem in ver1:
            if len(elem) == 2 and elem[0] == str(0):
                new_ver1.append(elem[1:])
            else:
                new_ver1.append(elem)
        version1 = f"{new_ver1[0]}.{new_ver1[1]}.{new_ver1[2]}"
        ver2 = v2.split(".")

        for elem in ver2:
            if len(elem) == 2 and str(elem[0]) == str(0):
                new_ver2.append(elem[1:])
            else:
                new_ver2.append(elem)
        version2 = f"{new_ver2[0]}.{new_ver2[1]}.{new_ver2[2]}"
        return version1, version2

    @staticmethod
    # Pour comparer la version locale et online
    def compversion_local(ver_loc, ver_online):  # (version locale, version online)
        compver = ""
        try:
            compver = semver.compare(ver_loc, ver_online)
        except Exception:
            log_error("%s", "%s", [""])
        return compver

    @staticmethod
    # Pour comparer avec la version minimal nécessaire du jeu
    def compversion_first_min_version(ver_locale, first_min_ver):
        compver = ""
        try:
            ver = VSUpdate.verif_formatversion(first_min_ver, ver_locale)
            compver = semver.compare(ver[0], ver[1])
        except Exception:
            log_error("%s", "%s", [""])
        return compver

    @staticmethod
    def get_max_version(versions):  # uniquement versions stables
        regexp_max_version = "v([\\d.]*)([\\W\\w]*)"
        max_version = re.search(regexp_max_version, max(versions))
        max_version = max_version[1]

        return max_version

    @staticmethod
    def get_changelog(url):
        # Scrap pour recuperer le changelog
        req_url = urllib.request.Request(url)
        log = {}
        lst_log_desc = []

        try:
            urllib.request.urlopen(req_url)
            req_page_url = requests.get(url, timeout=2)
            page = req_page_url.content
            soup = BeautifulSoup(page, features="html.parser")
            soup_full_changelog = soup.find("div", {"class": "changelogtext"})
            # version
            last_version = soup_full_changelog.find("strong").text
            # On regarde si formatage par <ul></ul>
            balise_ul = soup_full_changelog.find("li")

            if balise_ul is not None:
                lst_log_desc.append(balise_ul.text)
            else:
                # recherche des paragraphes, on remplace les balises <br>, </br>, <br/> par un saut de ligne \n
                regexp_br = r"</{0,1}br/{0,1}>"
                new_desc_log = re.sub(regexp_br, "\n", str(soup_full_changelog.p))
                # recherche des paragraphes, on remplace les balises </p> par un saut de ligne \n
                regexp_p = r"</{0,1}p>"
                new_desc_log_2 = re.sub(regexp_p, "\n", new_desc_log)
                # On supprime le tout premier \n
                regex_final_desc_log_01 = r"[\n]^"
                new_desc_log_3 = re.sub(regex_final_desc_log_01, "", new_desc_log_2)
                # On supprime le(s) dernier(s) \n en fin de chaine
                regex_final_desc_log = r"[\n]$"
                final_desc_log = re.sub(regex_final_desc_log, "", new_desc_log_3)
                # on separe la chaine au niveau de \n pour avoir un élément par ligne
                lst_log_desc = final_desc_log.split("\n")
                # On nettoie la liste
                for entry in lst_log_desc:
                    if entry == "":  # On supprime les entrées vide la liste
                        lst_log_desc.remove(entry)
                # On retire les caratceres spéciaux en début de ligne si il y en a
                for item in lst_log_desc:
                    index_item = lst_log_desc.index(item)
                    regex_carspe = r"^[\W*]*"
                    new_item = re.sub(regex_carspe, "", item)
                    lst_log_desc[int(index_item)] = new_item
            # #######
            log[last_version] = lst_log_desc
            log["url"] = url
        except requests.exceptions.ReadTimeout:
            log_error("%s", "%s", [lang_handler.get("read_timeout_error")])
        except urllib.error.URLError as err_url:
            # Affiche de l"erreur si le lien n"est pas valide
            log_error("%s: %s", "%s: %s", [err_url.reason, url])
        return log

    def accueil(
        self,
    ):  # le _ en debut permet de lever le message "Parameter "net_version" value is not used
        if self.gamever_limit == "100.0.0":
            self.version = lang_handler.get("version_max")
        else:
            self.version = self.gamever_limit
        # *** Texte d"accueil ***
        column, row = os.get_terminal_size()
        txt_title01 = f"\n\n[bold cyan]{lang_handler.get('title')} - v.{__version__} {lang_handler.get('by')} {__author__}[/bold cyan]"

        for line in txt_title01.splitlines():
            log_info("%s", "%s", [line.center(column)])
        # On vérifie si une version plus récente du script est en ligne
        txt_title02 = f"\n[cyan]{lang_handler.get('title2')} : [bold]{self.version}[/bold][/cyan]\n"

        for line in txt_title02.splitlines():
            log_info("%s", "%s", [line.center(column)])
        log_info("%s\n", "%s\n", [""])

    def mods_exclusion(self):
        # On crée la liste des mods à exclure de la maj
        for j in range(1, len(self.config_read.options("Mod_Exclusion")) + 1):
            try:
                modfile = self.config_read.get("Mod_Exclusion", f"mod{j}")
                if modfile != "":
                    self.mods_exclu.append(modfile)
                self.mods_exclu.sort()
            except configparser.NoSectionError:
                pass
            except configparser.InterpolationSyntaxError as err_parsing:
                log_error(
                    "Error in config.ini [Mod_Exclusion] - mod%s: %s",
                    "Error in config.ini [Mod_Exclusion] - mod%s: %s",
                    [j, err_parsing],
                )
                sys.exit()

    def mods_list(self):
        # Création de la liste des mods à mettre à jour
        # On retire les mods de la liste d"exclusion
        self.liste_mod_maj_filename = self.liste_complete_mods()
        for modexclu in self.mods_exclu:
            if modexclu in self.liste_mod_maj_filename:
                self.liste_mod_maj_filename.remove(
                    modexclu
                )  # contient la liste des mods à mettre a jour avec les noms de fichier

        for elem in self.liste_mod_maj_filename:
            name = self.extract_modinfo(elem)[0]
            self.mod_name_list.append(name[0])

    def update_mods(self):
        # Comparaison et maj des mods
        self.liste_mod_maj_filename.sort(key=lambda s: s.casefold())

        for mod_maj in self.liste_mod_maj_filename:
            modname_value = self.extract_modinfo(mod_maj)[0]
            self.version_locale = self.extract_modinfo(mod_maj)[2]
            modid_value = self.extract_modinfo(mod_maj)[1]
            if modid_value == "":
                modid_value = re.sub(r"\s", "", modname_value).lower()
            filename_value = self.extract_modinfo(mod_maj)[4]
            mod_url_api = f"{api_url}/{modid_value}"
            # On teste la validité du lien url
            req = urllib.request.Request(mod_url_api)

            try:
                urllib.request.urlopen(req)  # On teste l"existence du lien
                log_debug("%s", "%s", [mod_url_api])
                req_page = requests.get(mod_url_api, timeout=2)
                resp_dict = req_page.json()
                mod_asset_id = resp_dict["mod"]["assetid"]
                self.mod_last_version_online = resp_dict["mod"]["releases"][0][
                    "modversion"
                ]
                mod_file_onlinepath = resp_dict["mod"]["releases"][0]["mainfile"]
                mod_prerelease_value = semver.Version.parse(
                    self.mod_last_version_online
                )
                # compare les versions des mods
                log_info(
                    "[green]%s[/green]: %s : %s - %s : %s",
                    "%s: %s : %s - %s : %s",
                    [
                        modname_value,
                        lang_handler.get("compver1"),
                        self.version_locale,
                        lang_handler.get("compver2"),
                        self.mod_last_version_online,
                    ],
                )

                if (
                    self.disable_mod_dev == "false"
                    or mod_prerelease_value.prerelease is None
                ):
                    # On récupère les version du jeu nécessaire pour le mod (cad la version la plus basse necessaire)
                    mod_game_versions = resp_dict["mod"]["releases"][0]["tags"]
                    first_min_ver = None

                    for ver in mod_game_versions:
                        first_min_ver = ver.split("v", 1)[1]
                    result_compversion_local = self.compversion_local(
                        self.version_locale, self.mod_last_version_online
                    )  # (version locale, version online)
                    # On compare la version max souhaité à la version necessaire pour le mod
                    result_game_compare_version = self.compversion_first_min_version(
                        self.gamever_limit, first_min_ver
                    )  # (version locale, version online,)

                    if (
                        result_game_compare_version == -1
                        or result_game_compare_version == 0
                    ):  # On met à jour
                        if result_compversion_local == -1 or (
                            result_compversion_local == 0
                            and self.force_update.lower() == "true"
                        ):
                            dl_link = f"{mods_url}/{mod_file_onlinepath}"
                            resp = requests.get(dl_link, stream=True, timeout=2)
                            file_size = int(resp.headers.get("Content-length"))
                            file_size_mo = round(file_size / (1024**2), 2)
                            log_info(
                                "\t%s: %s %s",
                                "\t%s: %s %s",
                                [
                                    lang_handler.get("compver3"),
                                    file_size_mo,
                                    lang_handler.get("compver3a"),
                                ],
                            )
                            log_info(
                                "\t[green] %s v.%s[/green] %s",
                                "\t %s v.%s %s",
                                [
                                    modname_value,
                                    self.mod_last_version_online,
                                    lang_handler.get("compver4"),
                                ],
                            )

                            try:
                                os.remove(filename_value)
                            except PermissionError:
                                log_error("%s:", "%s:", [filename_value])
                                sys.exit()
                            # debug
                            wget.download(dl_link, str(paths.get_mods_path()))
                            self.changelog_path = f"{show_url}/{mod_asset_id}#tab-files"
                            # On récupère le changelog
                            log_txt = self.get_changelog(self.changelog_path)
                            content_lst_mods_updated = [
                                self.version_locale,
                                self.mod_last_version_online,
                                log_txt,
                            ]
                            self.mods_updated[modname_value] = content_lst_mods_updated
                            self.nb_maj += 1
            except requests.exceptions.ReadTimeout:
                log_error("%s", "%s", [lang_handler.get("read_timeout_error")])
            except urllib.error.URLError as err_url:
                # Affiche de l"erreur si le lien n"est pas valide
                log_error(
                    "%s: %s (%s)",
                    "%s: %s (%s)",
                    [err_url.reason, modname_value, mod_url_api],
                )
            except KeyError:
                log_error(
                    "%s\n%s",
                    "%s\n%s",
                    [modname_value, lang_handler.get("mod_local_deleted")],
                )
            except Exception:
                log_error(
                    "%s\n%s",
                    "%s\n%s",
                    [modname_value, lang_handler.get("mod_local_deleted")],
                )

    def resume(self):
        # Résumé de la maj
        def translated(self, summary1: str, summary2: str):
            log_info(
                "  [yellow]%s[/yellow]\n\n%s:\n\n\t\t\tMods Vintage Story - %s : %s\n\n",
                "  %s\n\n%s:\n\n\t\t\tMods Vintage Story - %s : %s\n\n",
                [
                    summary1,
                    summary2,
                    lang_handler.get("last_update"),
                    datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                ],
            )

            for modname, value in self.mods_updated.items():
                local_version = value[0]
                online_last_version = value[1]
                log_info(
                    " * [green]%s:[/green]: v%s -> v%s (%s):\n",
                    " * %s: v%s -> v%s (%s):\n",
                    [modname, local_version, online_last_version, value[2]["url"]],
                )

                for log_version, log_txt in value[2].items():
                    if log_version != "url":
                        log_info(
                            "\t[bold][yellow]Changelog %s:[/yellow][/bold]",
                            "\tChangelog %s:\n",
                            [log_version],
                        )

                        for line in log_txt:
                            log_info("\t\t[yellow]- %s[/yellow]", "\t\t- %s", [line])

        if self.nb_maj > 1:
            translated(self, lang_handler.get("summary1"), lang_handler.get("summary2"))
        elif self.nb_maj == 1:
            translated(self, lang_handler.get("summary3"), lang_handler.get("summary4"))
        else:
            log_info(
                "  [yellow]%s[/yellow]\n", "  %s\n", [lang_handler.get("summary5")]
            )

        if len(self.mods_exclu) == 1:
            modinfo_values = self.extract_modinfo(self.mods_exclu[0])
            log_info(
                "\n %s:\n - [red]%s [italic](v.%s)[italic][/red]",
                "\n %s:\n - %s (v.%s)",
                [lang_handler.get("summary6"), modinfo_values[0], modinfo_values[2]],
            )

        if len(self.mods_exclu) > 1:
            log_info("\n %s:", "\n %s:", [lang_handler.get("summary7")])

            for k in range(0, len(self.mods_exclu)):
                # On appelle la fonction pour extraire modinfo.json
                modinfo_values = self.extract_modinfo(self.mods_exclu[k])
                log_info(
                    " - [red]%s v.%s[/red]",
                    " - %s v.%s",
                    [modinfo_values[0], modinfo_values[2]],
                )


# Création du pdf.
class ModInfo:
    def __init__(self, mod_name, mod_id, mod_moddesc, mod_filepath):
        # path
        self.filepath = mod_filepath
        self.path_png = Path(paths.get_temp_path(), "png")
        self.path_modicon = None
        # dico
        self.modsinfo_dic = {}
        # list
        self.moddesc_lst = []
        # var
        self.mod_moddesc = mod_moddesc
        self.mod_name = mod_name
        self.mod_url = None
        self.mod_id = mod_id
        self.modinfo_content = None
        self.test_url_mod = ""

    def get_infos(self):
        # extraction modicon.png et renommage avec modid
        if zipfile.is_zipfile(self.filepath):
            archive = zipfile.ZipFile(self.filepath, "r")
            try:
                archive.extract("modicon.png", self.path_png)
                png_name = f"{self.mod_id}.png"
                self.path_modicon = Path(self.path_png, png_name)
                try:
                    os.rename(Path(self.path_png, "modicon.png"), self.path_modicon)
                except FileExistsError:
                    pass
            except KeyError:
                pass
            zipfile.ZipFile.close(archive)

        self.mod_url = self.get_url(self.mod_id)
        self.moddesc_lst.append(self.mod_moddesc)
        self.moddesc_lst.append(self.mod_url)
        self.moddesc_lst.append(self.path_modicon)
        self.modsinfo_dic[self.mod_name] = self.moddesc_lst

        # On crée le csv
        with open(
            paths.get_mods_table_csv_path(), "a", encoding="UTF-8", newline=""
        ) as csv_file:
            objet_csv = csv.writer(csv_file)

            for items in self.modsinfo_dic:
                objet_csv.writerow(
                    [
                        items,
                        self.modsinfo_dic[items][0],
                        self.modsinfo_dic[items][1],
                        self.modsinfo_dic[items][2],
                    ]
                )
        return self.modsinfo_dic

    def get_url(self, modid):
        url = os.path.join(api_url, modid)
        req = urllib.request.Request(url)

        try:
            urllib.request.urlopen(req)  # On teste l"existence du lien
            req_page = requests.get(url, timeout=2)
            resp_dict = req_page.json()
            mod_asset_id = str(resp_dict["mod"]["assetid"])
            mod_url_alias = str(resp_dict["mod"]["urlalias"])

            if mod_url_alias == "None":
                self.test_url_mod = f"{api_url}/{mod_asset_id}"
            else:
                self.test_url_mod = f"{mods_url}/{mod_url_alias}"

            return self.test_url_mod
        except requests.exceptions.ReadTimeout:
            log_error("%s", "%s", [lang_handler.get("read_timeout_error")])
        except urllib.error.URLError as err_url:
            # Affiche de l"erreur si le lien n"est pas valide
            log_error("%s: %s", "%s: %s", [err_url.reason, self.test_url_mod])
        except KeyError:
            log_error("%s", "%s", [""])
            answer = None

            while answer not in lang_handler.yesno():
                answer = Prompt.ask("Continue?", choices=lang_handler.yesno())

            if answer not in {lang_handler.yesno(0), lang_handler.yesno(2)}:
                sys.exit()


def makepdf() -> None:
    cur_dt = datetime.now()

    try:
        # On crée le pdf
        monpdf = FPDF("P", "mm", "A4")
        monpdf.add_font("FreeSans", "", str(Path("font", "FreeSans.ttf")))
        monpdf.add_font("FreeSansBold", "", str(Path("font", "FreeSansBold.ttf")))
        margintop_page = 10
        monpdf.set_top_margin(margintop_page)
        monpdf.set_auto_page_break(True, margin=10)
        monpdf.set_page_background((200, 215, 150))
        monpdf.add_page(same=True)
        nom_fichier_pdf = Path(
            paths.get_config_path(),
            f'VS_Mods_{cur_dt.strftime("%Y")}_{cur_dt.strftime("%m")}_{cur_dt.strftime("%d")}.pdf',
        )
        monpdf.oversized_images = "DOWNSCALE"
        monpdf.oversized_images_ratio = 5
        width_img = 180
        x = (210 - width_img) / 2
        monpdf.image("banner.png", x=x, y=5, w=width_img)
        # Titre
        monpdf.set_font("FreeSansBold", "", size=20)
        monpdf.set_text_color(0, 0, 0)  # Couleur RGB pour le titre
        monpdf.set_y(45)
        monpdf.cell(
            w=0,
            h=20,
            text=f"{lang_handler.get('pdfTitle')}",
            border=0,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
            fill=False,
        )
        table_data = []

        # On remplit la liste table_data
        with open(paths.get_mods_table_csv_path(), newline="") as csv_file:
            reader = csv.reader(csv_file, delimiter=",")
            for ligne in reader:
                table_data.append(ligne)

        with monpdf.table(
            first_row_as_headings=False,
            line_height=5,
            width=190,
            col_widths=(5, 55, 130),
        ) as table:
            for ligne in table_data:
                # cellule 1 - icone
                row = table.row()
                row.cell(img=ligne[3], img_fill_width=True, link=ligne[2])
                # cellule 2 - nom du mod
                monpdf.set_font("FreeSansBold", "", size=7)
                row.cell(ligne[0], link=ligne[2])
                # cellule 3 - description
                monpdf.set_font("FreeSans", "", size=7)
                row.cell(ligne[1])
    except Exception:
        log_error("%s", "%s", [""])
        sys.exit()

    try:
        monpdf.output(nom_fichier_pdf)
        log_info(
            "\n\n\t\t[blue]%s\n[/blue]",
            "\n\n\t\t%s\n",
            [lang_handler.get("makingpdfended")],
        )
    except PermissionError:
        log_error("%s", "%s", [lang_handler.get("ErrorCreationPDF")])


def main(args):
    logpath: str = (
        f"VS_ModsUpdater-{datetime.today().strftime('%Y-%m-%d-%H-%M-%S')}.log"
    )
    logpath: Path = Path(paths.get_logs_path(), logpath)
    logging.basicConfig(filename=str(logpath), level=logging.INFO)

    if paths.get_config_path() is None:
        raise Exception("OS not supported")

    if args.configfile:
        paths.set_current_config_file_path(Path(args.configfile))
    lang_handler = LanguageHandler(args.language)

    if args.modspath and Path(args.modspath).is_dir():
        paths.set_current_mods_path(Path(args.modspath))
    inst = VSUpdate()

    if (
        not (args.modspath and Path(args.modspath).is_dir())
        and paths.get_current_config_file_path().is_file()
    ):
        # On charge le fichier config.ini si --modspath non donné
        config_read = configparser.ConfigParser(allow_no_value=True, interpolation=None)
        config_read.read("config.ini", encoding="utf-8-sig")
        paths.set_current_mods_path(config_read.get("ModPath", "path"))

        # On récupère le dossier des mods par argument, sinon on definit par defaut

    inst.accueil()
    inst.mods_exclusion()
    inst.mods_list()
    inst.update_mods()
    inst.resume()

    # Création du pdf (si argument nopause est false)
    if args.nopause == "false" or args.makepdf == "true":
        make_pdf = None

        if args.makepdf == "false":
            while make_pdf not in lang_handler.yesno():
                make_pdf = Prompt.ask(
                    f"{lang_handler.get('makePDF')}", choices=lang_handler.yesno()
                )

        if make_pdf == lang_handler.yesno(0) or make_pdf == lang_handler.yesno(2):
            # Construction du titre
            string_asterisk: str = "*" * (len(lang_handler.get("makePDFTitle")) + 4)
            log_info(
                "\t[green]%s[/green]\n\t[green]* %s *[/green]\n\t[green]%s[/green]\n",
                "\t%s\n\t* %s *\n\t%s",
                [string_asterisk, lang_handler.get("makePDFTitle"), string_asterisk],
            )
            # uniquement pour avoir le nb de mods (plus rapide car juste listing)
            nb_mods: int = 0
            mod_files_path: list[str] = glob.glob(
                str(Path(paths.get_current_mods_path(), "*.*"))
            )

            for mod in mod_files_path:
                modfile_ext = os.path.splitext(mod)[1]

                if modfile_ext in [".zip", ".cs"]:
                    nb_mods += 1
            nb_mods_ok: int = 0

            for modfilepath in mod_files_path:
                modfile_ext = os.path.splitext(modfilepath)[1]

                if modfile_ext in [".zip", ".cs"]:
                    nb_mods_ok += 1
                    info_content = inst.extract_modinfo(modfilepath)
                    ModInfo(
                        info_content[0],
                        info_content[1],
                        info_content[3],
                        info_content[4],
                    ).get_infos()
                    log_info(
                        "\t\t%s %s/%s",
                        "\t\t%s %s/%s",
                        [lang_handler.get("addingmodsinprogress"), nb_mods_ok, nb_mods],
                    )
            makepdf()

            if args.makepdf == "false":
                input(f"{lang_handler.get('exiting_script')}")
        elif make_pdf in [
            lang_handler.get("no").lower(),
            lang_handler.get("no")[0].lower(),
        ]:
            log_info("%s", "%s", [lang_handler.get("end_of_prg")])


if __name__ == "__main__":
    # Définitions des arguments
    argParser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    argParser.add_argument(
        "--modspath", help="Path to the mods folder", required=False, type=Path
    )
    argParser.add_argument(
        "--configfile",
        help="Path to the config.ini",
        required=False,
        type=Path,
        default=Path(paths.get_config_path(), "config.ini"),
    )
    argParser.add_argument(
        "--language",
        help="Set the language file (Default=en_US - see the lang directory).",
        required=False,
        default="en_US",
    )
    argParser.add_argument(
        "--nopause",
        help="Disable the pause at the end of the script.",
        choices=["false", "true"],
        type=str,
        required=False,
        default="false",
    )
    argParser.add_argument(
        "--exclusion",
        help="Write filenames of mods with extension (in quotes) to be excluded (each separated by space).",
        nargs="+",
    )
    argParser.add_argument(
        "--forceupdate",
        help="Force ModsUpdater to download latest versions for ALL mods.",
        choices=["false", "true"],
        type=str,
        required=False,
        default="false",
    )
    argParser.add_argument(
        "--makepdf",
        help="Create a PDF file of all mods in mods folder.",
        choices=["false", "true"],
        type=str,
        required=False,
        default="false",
    )
    argParser.add_argument(
        "--disable_mod_dev",
        help="Enable or disable the update of mods in dev or prerelease",
        choices=["false", "true"],
        type=str,
        required=False,
        default="false",
    )
    args = argParser.parse_args()
    # Fin des arguments

    main(args)
