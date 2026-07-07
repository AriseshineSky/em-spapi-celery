# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import io

from cmutils import logger

try:
    from ConfigParser import ConfigParser, RawConfigParser
except ImportError:
    from configparser import ConfigParser, RawConfigParser, NoOptionError

import yaml


class ConfigLoader(object):
    def load(self):
        raise NotImplementedError()


class IniConfigLoader(ConfigParser):
    section = ""
    config = None

    def __init__(self, config_path):
        self.config_path = os.path.abspath(os.path.expanduser(config_path))

        if not os.path.isfile(self.config_path):
            raise ValueError('Could not find configuration file - {}'.format(config_path))

        self.config = RawConfigParser()
        self.config.read(config_path)

    def set_section(self, section):
        self.section = section

    def get(self, key):
        if self.section:
            try:
                return self.config.get(self.section, key)
            except NoOptionError:
                message_info = [self.section, str(key), "ConfigTool.error", "no_key"]
                logger.error("|".join(message_info))
                return None
        else:
            return None

    def get_all_dict(self):
        configs = {}
        lists = self.config.items(self.section)
        for l in lists:
            configs[l[0]] = l[1]

        return configs

    def get_all(self):
        return self.config.items(self.section)

    def get_section_key(self, section, key):
        return self.config.get(section, key)

    def get_section_all(self, section):
        return self.config.items(section)

    def load(self):
        config = dict()
        cp = ConfigParser()
        cp.read(self.config_path)
        for section in cp.sections():
            config[section] = dict()
            for opt, val in cp.items(section):
                config[section][opt] = val

        return config


class YamlConfigLoader(ConfigLoader):
    def __init__(self, config_path):
        self._config_path = os.path.abspath(os.path.expanduser(config_path))

        if not os.path.isfile(self._config_path):
            raise ValueError('Could not find configuration file - {}'.format(config_path))

    def load(self):
        cfg = None
        with io.open(self._config_path, encoding='utf-8', errors='ignore') as fh:
            cfg = yaml.load(fh.read(), Loader=yaml.SafeLoader)

        return cfg
