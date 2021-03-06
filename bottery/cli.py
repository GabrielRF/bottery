'''
██████╗  ██████╗ ████████╗████████╗███████╗██████╗ ██╗   ██╗
██╔══██╗██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗╚██╗ ██╔╝
██████╔╝██║   ██║   ██║      ██║   █████╗  ██████╔╝ ╚████╔╝
██╔══██╗██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗  ╚██╔╝
██████╔╝╚██████╔╝   ██║      ██║   ███████╗██║  ██║   ██║
╚═════╝  ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝
'''

import importlib
import logging.config
import os
import shutil

import click

import bottery
from bottery.log import DEFAULT_LOGGING

logging.config.dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger('bottery')


def debug_option(f):
    @click.option('--debug/--no-debug', default=False)
    def wrapper(*args, **kwargs):
        if kwargs.get('debug', False):
            logger.setLevel(logging.DEBUG)
        return f(*args, **kwargs)

    return wrapper


@click.group()
def cli():
    """Bottery"""


@cli.command('startproject')
@click.argument('name')
def startproject(name):
    # Must validate projects name before creating its folder
    project_dir = os.path.join(os.getcwd(), name)
    os.mkdir(project_dir)

    # There's probably a better way to do this :)
    template_dir = os.path.join(bottery.__path__[0], 'conf/project_template')
    for root, dirs, files in os.walk(template_dir):
        for filename in files:
            new_filename = filename[:-4]  # Removes "-tpl"
            src = os.path.join(template_dir, filename)
            dst = os.path.join(project_dir, new_filename)
            shutil.copy(src, dst)


@cli.command('run')
@click.option('--port', default=8000, type=int)
@debug_option
def run(port, debug):
    """
    Run a web server to handle webhooks requests from all platforms
    configured on the project settings.
    """

    # .py vs init config file
    # Check how Lektor discover settings files
    # https://github.com/lektor/lektor/blob/master/lektor/project.py#L67-L79
    from aiohttp import web

    from bottery.conf import settings

    _bottery = click.style('bottery', fg='green')
    logger.debug('Running {} \o/'.format(_bottery))

    app = web.Application()

    platforms = settings.PLATFORMS.values()
    if not platforms:
        # Raise an expcetion if no platform is configured at settings.py
        raise Exception('No platforms configured')

    for platform in platforms:
        # For each platform found on settings.py, create an instance
        # and run its `configure` method. Once it's configured, create
        # a route for its handler.
        logger.debug('Importing engine %s', platform['ENGINE'])
        mod = importlib.import_module(platform['ENGINE'])
        engine = mod.engine(**platform['OPTIONS'])
        logger.debug('[%s] Configuring', engine.platform)
        engine.configure()
        logger.debug('[%s] Ready', engine.platform)
        app.router.add_route('POST', engine.webhook_endpoint, engine.handler)

    logger.debug('Running server')
    web.run_app(app, port=port, print=lambda x: None)
