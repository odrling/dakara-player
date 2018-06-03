import os
import logging
from tempfile import TemporaryDirectory
from contextlib import ExitStack

import coloredlogs
import yaml

from .version import __version__, __date__
from .safe_workers import WorkerSafeThread, Runner
from .text_generator import TextGenerator
from .vlc_player import VlcPlayer
from .dakara_server import DakaraServer
from .dakara_manager import DakaraManager
from .font_loader import get_font_loader_class
FontLoader = get_font_loader_class()


LOGLEVEL = 'INFO'


logger = logging.getLogger("dakara_player_vlc")


coloredlogs.install(
        fmt='[%(asctime)s] %(name)s %(levelname)s %(message)s',
        level=LOGLEVEL
        )


class DakaraPlayerVlc(Runner):
    """ Class associated with the main thread

        It simply starts, launchs the worker and waits for it to terminate or
        for a user Ctrl+C to be fired.
    """
    def init_runner(self, config_path, debug):
        """ Initialization

            Creates the worker stop event

            Args:
                config_path (str): path to the config file. Will be passed to
                    the worker, who uses it.
                debug (bool): run in debug mode.
        """
        # store arguments
        self.config_path = config_path
        self.debug = debug

        logger.debug("Started main")

    def run(self):
        """ Launch the worker and wait for the end
        """
        self.run_safe(DakaraWorker, self.config_path, self.debug)


class DakaraWorker(WorkerSafeThread):
    """ Class associated with the worker thread

        It simply starts, loads configuration, set the different worker,
        launches the main polling thread and waits for the end.
    """
    def init_worker(self, config_path, debug):
        """ Initialization

            Load the config and set the logger loglevel.

            Args:
                config_path (str): path to the config file.
                debug (bool): run in debug mode.
        """
        # load config
        self.config = self.load_config(config_path, debug)

        # configure loader
        self.configure_logger()
        logger.debug("Starting worker")

        # set thread
        self.thread = self.create_thread(target=self.run)

        logger.info("Dakara player {} ({})".format(
            __version__,
            __date__
            ))

    def run(self):
        """ Worker main method

            It sets up the different workers and uses them as context
            managers, which guarantee that their different clean methods will
            be called prorperly.

            Then it starts the polling thread and waits for the end.

            When `run` is called, the end can come for several reasons:
                * the main thread (who calls the worker thread) has caught a
                  Ctrl+C from the user;
                * an exception has been raised within the `run` method
                  (directly in the worker thread);
                * an exception has been raised within the polling thread.
        """
        # get the different workers as context managers
        # ExitStack makes the management of multiple context managers simpler
        # This mechanism plus the use of Worker classes allow to gracelly end
        # the execution of any thread within the context manager. It guarantees
        # as well that on leaving this context manager, all cleanup tasks will
        # be executed.
        with ExitStack() as stack:
            # temporary directory
            tempdir = stack.enter_context(TemporaryDirectory(
                    suffix='.dakara'
                    ))

            # font loader
            font_loader = stack.enter_context(FontLoader())
            font_loader.load()

            # text screen generator
            text_generator = TextGenerator(
                    self.config['player'].get('templates') or {},
                    tempdir
                    )

            # vlc player
            vlc_player = stack.enter_context(VlcPlayer(
                    self.stop,
                    self.errors,
                    self.config['player'],
                    text_generator
                    ))

            # communication with the dakara server
            dakara_server = DakaraServer(self.config['server'])
            dakara_server.authenticate()

            # manager for the precedent workers
            dakara_manager = stack.enter_context(DakaraManager(
                    self.stop,
                    self.errors,
                    font_loader,
                    vlc_player,
                    dakara_server
                    ))

            # start the worker thread
            dakara_manager.timer.start()

            # wait for stop event
            self.stop.wait()

            # leaving this method means leaving all the context managers and
            # stop the program

    @staticmethod
    def load_config(config_path, debug):
        """ Load the config from config file

            Args:
                config_path: path to the config file.
                debug (bool): run in debug mode.

            Returns:
                dictionary of the config.
        """
        logger.info("Reading config file '{}'".format(config_path))

        # check the config file is present
        if not os.path.isfile(config_path):
            raise IOError("No config file found")

        # load and parse the file
        with open(config_path) as file:
            try:
                config = yaml.load(file)

            except yaml.parser.ParserError as error:
                raise IOError("Unable to read config file") from error

        # check file content
        for key in ('player', 'server'):
            if key not in config:
                raise ValueError(
                    "Invalid config file, missing '{}'".format(key)
                )

        # if debug is set as argument, override the config
        if debug:
            config['loglevel'] = 'DEBUG'

        return config

    def configure_logger(self):
        """ Set the logger config

            Set a validated logging level from configuration.
        """
        # select logging level
        loglevel = self.config.get('loglevel', LOGLEVEL)
        loglevel_numeric = getattr(logging, loglevel.upper(), None)
        if not isinstance(loglevel_numeric, int):
            raise ValueError(
                    "Invalid loglevel in config file: '{}'".format(loglevel)
                    )

        coloredlogs.set_level(loglevel_numeric)