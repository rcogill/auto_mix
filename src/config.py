'''
This module loads a collection of configuration settings
from a YAML file and saves them in a dictionary.

This configuration dictionary is globally available within
any other module that imports the config module.
'''

import yaml

conf = {}

def load_conf(config_file = 'conf.yaml'):

    global conf

    f = open(config_file,'r')
    conf = yaml.load(f.read())
    f.close()

    return True