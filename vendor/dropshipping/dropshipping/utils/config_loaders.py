# -*- coding: utf-8 -*-

# Copyright © 2018 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
from io import open
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import yaml


class ConfigLoader(object):
    def load_config(self, *args, **kwargs):
        raise NotImplementedError()


class FileConfigLoader(ConfigLoader):
    def load_config(self, *args, **kwargs):
        if 'config_path' not in kwargs:
            raise ValueError('"config_path" is required to use FileConfigLoader')

        config_path = os.path.abspath(os.path.expanduser(kwargs['config_path']))
        if not os.path.isfile(config_path):
            raise ValueError('Could not find configuration file - %s' % kwargs['config_path'])

        with open(kwargs['config_path'], encoding='utf-8', errors='ignore') as config_fh:
            config = config_fh.read()

        return config


class IniConfigLoader(ConfigParser):
    def load_config(self, *args, **kwargs):
        config = dict()
        if 'config_path' not in kwargs:
            raise ValueError('"config_path" is required to use IniConfigLoader')

        config_path = os.path.abspath(os.path.expanduser(kwargs['config_path']))
        if not os.path.isfile(config_path):
            raise ValueError('Could not find configuration file - %s' % kwargs['config_path'])

        cp = ConfigParser()
        cp.read(config_path)
        for section in cp.sections():
            config[section] = dict()
            for opt, val in cp.items(section):
                config[section][opt] = val

        return config


class YamlConfigLoader(ConfigParser):
    def load_config(self, *args, **kwargs):
        config = dict()
        if 'config_path' not in kwargs:
            raise ValueError('"config_path" is required to use YamlConfigLoader')

        config_path = os.path.abspath(os.path.expanduser(kwargs['config_path']))
        if not os.path.isfile(config_path):
            raise ValueError('Could not find configuration file - %s' % kwargs['config_path'])

        with open(config_path) as fh:
            config = yaml.load(fh.read(), Loader=yaml.SafeLoader)

        return config
