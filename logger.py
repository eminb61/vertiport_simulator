import logging

import logging
from datetime import datetime, timedelta

class SimTimeFormatter(logging.Formatter):
    def __init__(self, sim_env, start_datetime, fmt='%(sim_time)s - %(levelname)s - %(message)s'):
        super().__init__(fmt)
        self.sim_env = sim_env
        # Assume start_datetime is a datetime.datetime object representing the start of the simulation
        self.start_datetime = start_datetime

    def format(self, record):
        # Convert simulation time (in hours) to a datetime object
        sim_datetime = self.start_datetime + timedelta(hours=self.sim_env.now)
        # Format the simulation datetime as %Y%m%d_%H%M%S
        record.sim_time = sim_datetime.strftime('%Y-%m-%d %H:%M:%S')
        return super().format(record)

class Logger:
    def __init__(self, env, simulation_start_datetime, is_logging=True):
        self.env = env
        self.start_datetime = simulation_start_datetime
        self.logger = logging.getLogger(__name__)
        if is_logging:
            self.setup_logger()
        else:
            self.logger.addHandler(logging.NullHandler())
            # self.logger.setLevel(logging.NOTSET)
    
    def setup_logger(self):
        self.logger.setLevel(logging.INFO)
        self.logger_path = f"logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.handler = logging.FileHandler(self.logger_path)        
        # Set logger name using the current date time
        # Use the custom formatter with simulation time and start datetime
        self.formatter = SimTimeFormatter(self.env, self.start_datetime)
        self.handler.setFormatter(self.formatter)

        self.logger.addHandler(self.handler)

    def log(self, message):
        self.logger.info(message)

    def debug(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.debug(*args, **kwargs)
    
    def info(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.info(*args, **kwargs)
    
    def warning(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.error(*args, **kwargs)
    
    def critical(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.critical(*args, **kwargs)        

    def close(self):
        self.logger.removeHandler(self.handler)
        self.handler.close()