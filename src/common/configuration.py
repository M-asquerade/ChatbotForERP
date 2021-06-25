# coding: utf-8
#==================================================================================================
"""
This model is used to read all the file of configurations and manage all the configurations.
"""
# Author : Shengzhe ZHANG
# Date   : 14/05/2021
#==================================================================================================

import importlib

class Configuration(object):
    __first_init = False
    __instance = False

    # Singleton
    def __new__(cls):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        # Default option is voltmeter GT2000 1.8KV
        # Verifier le voltmeter n'est pas initialise encore(singleton)
        if not Configuration.__first_init:
            Configuration.__first_init = True

            # load the database configuration
            loader = importlib.machinery.SourceFileLoader('database', './configs/chatbot.conf')
            spec = importlib.util.spec_from_loader(loader.name, loader)
            self.__dabatase = importlib.util.module_from_spec(spec)
            loader.exec_module(self.__dabatase)

    @staticmethod
    def config():
        """
        return the only instance of the class
        """
        return Configuration.__instance

    def database_host(self):
        return self.__dabatase.DATABASE_HOST

    def database_port(self):
        return self.__dabatase.DATABASE_PORT

    def database_user(self):
        return self.__dabatase.DATABASE_USER

    def database_password(self):
        return self.__dabatase.DATABASE_PASSWORD

    def database_name(self):
        return self.__dabatase.DATABASE_NAME

