from ocean import main
from ocean.logger import logger

if __name__ == '__main__':
    app = main.create_app('config.DevelopmentConfig')
    if app is None:
        logger.fatal('Exiting program...')
        exit(1)
    logger.info('Starting application')
    app.run()
