import yaml

conf = {}

def load_conf(config_file = 'conf.yaml'):

    global conf

    f = open(config_file,'r')
    conf = yaml.load(f.read())
    f.close()