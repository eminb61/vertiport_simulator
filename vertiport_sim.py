from helpers import generate_ids
from logger import Logger
import simpy
import random
import numpy as np
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta



class VertiportSimulation:
    def __init__(self, 
                 env, 
                 aircraft_ids, 
                 passenger_ids, 
                 aircraft_mean_interarrival_time, 
                 passenger_mean_interarrival_time,
                 num_park,
                 tlof_mean_service_time,
                 charge_mean_service_time,
                 seat_capacity,
                 termination_event,
                 stochastic,
                 terminal_buffer_capacity,
                 tlof_feedback=True,
                 blocking=False,
                 is_logging=False,
                 seed=0):
        self.env = env
        self.aircraft_ids = iter(aircraft_ids)  # Make iterators
        self.passenger_ids = iter(passenger_ids)
        self.aircraft_mean_interarrival_time = aircraft_mean_interarrival_time
        self.passenger_mean_interarrival_time = passenger_mean_interarrival_time
        self.num_park = num_park
        self.tlof_mean_service_time = tlof_mean_service_time
        self.charge_mean_service_time = charge_mean_service_time/self.num_park
        self.seat_capacity = seat_capacity
        self.termination_event = termination_event
        self.stochastic = stochastic
        self.tlof_feedback = tlof_feedback
        self.blocking = blocking
        self.terminal_buffer_capacity = terminal_buffer_capacity
        self.is_logging = is_logging
        self.simulation_start_datetime = datetime(2024, 1, 1)
        self.seed = seed

        # Servers and queues
        self.tlof_server = simpy.PriorityResource(env, capacity=1)
        self.tlof_server2 = simpy.PriorityResource(env, capacity=1)
        self.park_server = simpy.Resource(env, capacity=1)
        self.passenger_queue = []
        self.aircraft_departure_queue = simpy.Store(env)
        # Statistics
        self.waiting_times = defaultdict(lambda: defaultdict(dict))
        self.arrival_departure_times = defaultdict(lambda: defaultdict(dict))
        self.arrival_departure_counter = defaultdict(lambda: defaultdict(dict))
        self.queue_lengths = defaultdict(lambda: defaultdict(dict))
        self.in_service_counts = defaultdict(lambda: defaultdict(dict))
        self.time_logs = defaultdict(lambda: defaultdict(dict))
        self.process_times = defaultdict(lambda: defaultdict(dict))
        self.rejected_aircraft_counter = 0
        self.surface_aircraft_count = defaultdict(dict)
        self.departing_passenger_queue_length = 0
        self.passenger_service_queue_length = 0
        self.terminal_store = simpy.Store(env, capacity=self.terminal_buffer_capacity)
        self.surface_store = simpy.Store(env, capacity=1)
        # Populate the surface store with the number of parking spots
        # for i in range(num_park):
        #     self.surface_store.put('park')
        self.surface_store.put('park')
        
        # If terminal buffer capacity is not infinite, then populate the terminal store with the capacity
        if self.terminal_buffer_capacity != np.inf:
            for _ in range(self.terminal_buffer_capacity):
                self.terminal_store.put('capacity')

        # Initiate arrival_departure_counter to zero
        self.arrival_departure_counter['aircraft']['arrival_counter'][0] = 0
        self.arrival_departure_counter['aircraft']['departure_counter'][0] = 0
        self.arrival_departure_counter['passenger']['arrival_counter'][0] = 0
        self.arrival_departure_counter['passenger']['departure_counter'][0] = 0
        # Initiate queue lengths to zero
        self.queue_lengths['aircraft_arrival_queue'][0] = 0
        self.queue_lengths['aircraft_departure_queue'][0] = 0
        self.queue_lengths['passenger_queue'][0] = 0
        self.queue_lengths['park_queue_length'][0] = 0

        self.surface_aircraft_count[0] = 0
        self.logger = Logger(env, self.simulation_start_datetime, self.is_logging)

        # Seed the random number generator
        random.seed(seed)
        np.random.seed(seed)

    def convert_hr_to_dt(self, hour: float) -> str:
        """
        Converts the hour to a datetime string.
        """
        return (self.simulation_start_datetime + timedelta(hours=hour)).strftime('%Y-%m-%d %H:%M:%S')

    def update_counter(self, agent_type: str, counter: dict, counter_type: str, change: int):
        last_value = self.get_latest_value(agent_type, counter, counter_type)
        time = self.is_time_overlapping(self.env.now, agent_type, counter)
        counter[agent_type][counter_type][time] = last_value + change

    def get_latest_value(self, agent_type: str, counter: dict, counter_type: str):
        return list(counter[agent_type][counter_type].values())[-1]
    
    def get_latest_value_from_dict(self, counter: dict):
        return list(counter.values())[-1]
    
    def get_latest_queue_length(self, counter: dict, counter_type: str):
        if len(counter[counter_type]) == 0:
            return 0
        return list(counter[counter_type].values())[-1]
    
    def update_aircraft_arrival_queue_length(self, update):
        # Save the tlof queue length
        time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
        # Get the last value of the tlof queue length
        queue_length = self.get_latest_queue_length(counter=self.queue_lengths, counter_type='aircraft_arrival_queue')
        self.queue_lengths['aircraft_arrival_queue'][time] = queue_length + update 

    def update_park_queue_length(self, update):
        # Save the park queue length
        time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
        # Get the last value of the park queue length
        queue_length = self.get_latest_queue_length(counter=self.queue_lengths, counter_type='park_queue_length')
        self.queue_lengths['park_queue_length'][time] = queue_length + update

    def update_aircraft_departure_queue_length(self, update):
        # Save the tlof queue length
        time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
        # Get the last value of the tlof queue length
        queue_length = self.get_latest_queue_length(counter=self.queue_lengths, counter_type='aircraft_departure_queue')
        self.queue_lengths['aircraft_departure_queue'][time] = queue_length + update

    def update_passenger_queue_length(self, update):
        # Save the tlof queue length
        time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
        # Get the last value of the tlof queue length
        queue_length = self.get_latest_queue_length(counter=self.queue_lengths, counter_type='passenger_queue')
        self.queue_lengths['passenger_queue'][time] = queue_length + update

    def update_passenger_service_queue_length(self, update):
        # Save the tlof queue length
        time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
        # Get the last value of the tlof queue length
        queue_length = self.get_latest_queue_length(counter=self.queue_lengths, counter_type='passenger_service_queue')
        self.queue_lengths['passenger_service_queue'][time] = queue_length + update

    def aircraft_arrival_process(self):
        while True:
            if self.stochastic:
                yield self.env.timeout(np.random.exponential(self.aircraft_mean_interarrival_time))
            else:
                yield self.env.timeout(self.aircraft_mean_interarrival_time)
            try:
                aircraft_id = next(self.aircraft_ids)
                time = self.is_time_overlapping(self.env.now, 'aircraft', self.arrival_departure_times)
                self.arrival_departure_times['aircraft'][aircraft_id]['arrival_time'] = time
                
                self.logger.debug(f"{aircraft_id} will request terminal buffer at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at terminal buffer: {self.terminal_buffer_capacity - len(self.terminal_store.items)}")
                if self.terminal_buffer_capacity != np.inf and len(self.terminal_store.items) == 0:
                    self.logger.debug(f"{aircraft_id} rejected at {self.convert_hr_to_dt(self.env.now)}")
                    # last_value = self.get_latest_value_from_dict(self.rejected_aircraft_counter)
                    self.rejected_aircraft_counter += 1
                    continue
                else:
                    # Increase the arrival counter
                    self.update_counter('aircraft', self.arrival_departure_counter, 'arrival_counter', 1)
            
                    self.env.process(self.terminal_arrival_process(aircraft_id))
            except StopIteration:
                break  # No more pre-generated aircraft IDs 

        self.termination_event.succeed()      

    def terminal_arrival_process(self, aircraft_id):
        # Request a space from the terminal airspace
        # yield self.env.timeout(0)
        if self.terminal_buffer_capacity == np.inf:
            self.terminal_store.put('capacity')
        
        # Get on the terminal buffer
        yield self.env.process(self.request_terminal_buffer(aircraft_id))

        start_time = self.env.now

        # If the there is a blocking, the aircraft first need to secure a parking space before it can proceed to the tlof
        if self.blocking:
            yield self.env.process(self.request_surface(aircraft_id))
            
        self.env.process(self.turnaround_process(aircraft_id, start_time))

    def request_terminal_buffer(self, aircraft_id):
        yield self.terminal_store.get()
        # Save the terminal queue length
        self.update_aircraft_arrival_queue_length(update=1)
        self.logger.debug(f"{aircraft_id} entered the terminal buffer at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at terminal buffer: {self.terminal_buffer_capacity - len(self.terminal_store.items)}")
        self.logger.debug(f"Number of aircraft at the terminal buffer from queue length counter: {list(self.queue_lengths['aircraft_arrival_queue'].values())[-1]}")

    def request_surface(self, aircraft_id):
        yield self.surface_store.get()
        self.logger.debug(f"{aircraft_id} got the surface reservation at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at surface: {self.num_park - len(self.surface_store.items)}")

    def turnaround_process(self, aircraft_id, start_time):
        # TLOF and Park handling with exponential service times
        with self.tlof_server.request(priority=0) as request:
            yield request
            # Update the arrival queue length
            self.update_aircraft_arrival_queue_length(update=-1)            
            # Open space in the terminal buffer
            self.terminal_store.put('capacity')
            self.logger.debug(f"{aircraft_id} left the terminal buffer at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at terminal buffer: {self.terminal_buffer_capacity - len(self.terminal_store.items)}")
            self.logger.debug(f"Number of aircraft at the terminal buffer from queue length counter: {list(self.queue_lengths['aircraft_arrival_queue'].values())[-1]}")
            # Save the tlof queue waiting time
            self.waiting_times['aircraft'][aircraft_id]['tlof_arrival_queue_waiting_time'] = self.env.now - start_time
            # Get the landing process time
            if self.stochastic:
                landing_process_time = np.random.exponential(self.tlof_mean_service_time)
            else:
                landing_process_time = self.tlof_mean_service_time
            # Save the landing process time
            yield self.env.timeout(landing_process_time)
        # Save the landing process time
        self.process_times['aircraft'][aircraft_id]['landing_process_time'] = landing_process_time

        # Increase the surface count
        last_value = self.get_latest_value_from_dict(self.surface_aircraft_count)
        self.surface_aircraft_count[self.env.now] = last_value + 1
        # Log the surface count
        self.logger.debug(f"{aircraft_id} landed at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at surface: {self.num_park - len(self.surface_store.items)}")
        
        start_time = self.env.now
        # Save the park queue length
        self.update_park_queue_length(update=1)

        with self.park_server.request() as request:
            yield request
            # Log parking time
            self.logger.debug(f"{aircraft_id} parked at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at surface: {self.num_park - len(self.surface_store.items)}")
            # Update the park queue length
            self.update_park_queue_length(update=-1)
            self.waiting_times['aircraft'][aircraft_id]['park_queue_waiting_time'] = self.env.now - start_time
            if self.stochastic:
                charge_process_time = np.random.exponential(self.charge_mean_service_time)
            else:
                charge_process_time = self.charge_mean_service_time
            yield self.env.timeout(charge_process_time)
            # Save the charge time
            self.process_times['aircraft'][aircraft_id]['charge_process_time'] = charge_process_time
        # Put aircraft in the the available departure queue
        self.aircraft_departure_queue.put(aircraft_id)
        self.time_logs['aircraft'][aircraft_id]['departure_queue_enter_time'] = self.env.now

        self.logger.debug(f"{aircraft_id} charged and entered the departure queue at {self.convert_hr_to_dt(self.env.now)}. Num aircraft at surface: {self.num_park - len(self.surface_store.items)}")
        self.logger.debug(f"Number of aircraft at the departure queue: {list(self.queue_lengths['aircraft_departure_queue'].values())[-1]}")

    def passenger_process(self):
        while True:
            if self.stochastic:
                yield self.env.timeout(np.random.exponential(self.passenger_mean_interarrival_time))
            else:
                yield self.env.timeout(self.passenger_mean_interarrival_time)
            try:
                passenger_id = next(self.passenger_ids)
                time = self.is_time_overlapping(self.env.now, 'passenger', self.arrival_departure_times)
                self.arrival_departure_times['passenger'][passenger_id]['arrival_time'] = self.env.now
                # Increase the arrival counter
                self.update_counter(agent_type='passenger', counter=self.arrival_departure_counter, counter_type='arrival_counter', change=1)
                self.passenger_service_queue_length += 1

                # self.update_passenger_service_queue_length(update=1)
                # Save the tlof queue length
                time = self.is_time_overlapping(time=self.env.now, agent_type='queue', tracker=self.queue_lengths)
                # Get the last value of the tlof queue length
                self.queue_lengths['passenger_service_queue'][time] = self.passenger_service_queue_length   

                # Log the passenger arrival
                self.logger.debug(f"{passenger_id} arrived at {self.convert_hr_to_dt(self.env.now)}. Num passengers at passenger service queue: {list(self.queue_lengths['passenger_service_queue'].values())[-1]}")
                self.logger.debug(f"Number of passengers at the passenger service queue counter: {self.passenger_service_queue_length}")
                    
                self.passenger_queue.append(passenger_id)
                # Save the passenger queue length
                # time = self.is_time_overlapping(self.env.now, 'passenger', self.queue_lengths)
                # self.queue_lengths['passenger_queue'][time] = len(self.passenger_queue)

                if len(self.passenger_queue) >= self.seat_capacity:

                    time = self.is_time_overlapping(self.env.now, 'queue', self.queue_lengths)
                    self.queue_lengths['passenger_service_queue'][time] = self.passenger_service_queue_length             
                    self.env.process(self.pool_passengers())

            except StopIteration:
                break  # No more pre-generated passenger IDs

    def get_aircraft_from_departure_queue(self):
        aircraft_id = yield self.aircraft_departure_queue.get()
        return aircraft_id
        
    def pool_passengers(self):
        departing_passengers = [self.passenger_queue.pop(0) for _ in range(self.seat_capacity)]
        # Get available aircraft from the departure queue
        aircraft_id = yield self.aircraft_departure_queue.get()
        # aircraft_id = self.env.process(self.get_aircraft_from_departure_queue())

        self.time_logs['aircraft'][aircraft_id]['departure_queue_exit_time'] = self.env.now
        # Update the departure queue length
        self.update_aircraft_departure_queue_length(update=1)
        # Log the passenger departure and aircraft departure
        self.logger.debug(f"{departing_passengers} assigned to {aircraft_id} at {self.convert_hr_to_dt(self.env.now)}. Num passengers at passenger service queue: {list(self.queue_lengths['passenger_service_queue'].values())[-1]}")
        self.logger.debug(f"Departure queue length: {list(self.queue_lengths['aircraft_departure_queue'].values())[-1]}")
        # If there are more passengers than the seat capacity, get the first 4 passengers. If there are less than seat_capacity, get all passengers
        # num_pax = len(self.passenger_queue) if len(self.passenger_queue) < self.seat_capacity else self.seat_capacity
        
        self.departing_passenger_queue_length += len(departing_passengers)
        for passenger_id in departing_passengers:
            self.time_logs['passenger'][passenger_id]['departure_queue_exit_time'] = self.env.now
            self.waiting_times['passenger'][passenger_id]['waiting_time'] = self.env.now - self.arrival_departure_times['passenger'][passenger_id]['arrival_time']

        # Blocking of the surface ends here.
        self.surface_store.put('park')
        # Decrese the surface count
        last_value = self.get_latest_value_from_dict(self.surface_aircraft_count)
        self.surface_aircraft_count[self.env.now] = last_value - 1

        # Log surface count
        self.logger.debug(f"Num aircraft at surface: {self.num_park - len(self.surface_store.items)}")
        
        self.env.process(self.departure_process(aircraft_id))

    def departure_process(self, aircraft_id):
        start_time = self.env.now

        if self.tlof_feedback:
            # Request the tlof server
            with self.tlof_server.request(priority=1) as request:
                yield request
                # Save the pushback time
                self.arrival_departure_times['aircraft'][aircraft_id]['pushback_time'] = self.env.now
                # Update the departure queue length
                self.update_aircraft_departure_queue_length(update=-1)            
                # # Update the passenger queue length
                # self.update_passenger_service_queue_length(update=-self.seat_capacity)

                self.passenger_service_queue_length -= self.seat_capacity
                
                time = self.is_time_overlapping(self.env.now, 'queue', self.queue_lengths)
                self.queue_lengths['passenger_service_queue'][time] = self.passenger_service_queue_length            

                # Save the tlof queue waiting time
                self.waiting_times['aircraft'][aircraft_id]['tlof_departure_queue_waiting_time'] = self.env.now - start_time
                if self.stochastic:
                    departure_process_time = np.random.exponential(self.tlof_mean_service_time)
                else:
                    departure_process_time = self.tlof_mean_service_time
                yield self.env.timeout(departure_process_time)
        else:
            with self.tlof_server2.request(priority=1) as request:
                yield request
                # Save the pushback time
                self.arrival_departure_times['aircraft'][aircraft_id]['pushback_time'] = self.env.now
                # Update the departure queue length
                self.update_aircraft_departure_queue_length(update=-1)            
                # # Update the passenger queue length
                self.passenger_service_queue_length -= self.seat_capacity
                
                time = self.is_time_overlapping(self.env.now, 'queue', self.queue_lengths)
                self.queue_lengths['passenger_service_queue'][time] = self.passenger_service_queue_length            

                # Save the tlof queue waiting time
                self.waiting_times['aircraft'][aircraft_id]['tlof_departure_queue_waiting_time'] = self.env.now - start_time
                if self.stochastic:
                    departure_process_time = np.random.exponential(self.tlof_mean_service_time)
                else:
                    departure_process_time = self.tlof_mean_service_time
                yield self.env.timeout(departure_process_time)
        # Save the tlof service time
        self.process_times['aircraft'][aircraft_id]['departure_process_time'] = departure_process_time
        # Update the departure counter
        self.update_counter('aircraft', self.arrival_departure_counter, 'departure_counter', 1)
        # Save passenger departure count
        self.update_counter(agent_type='passenger', counter=self.arrival_departure_counter, counter_type='departure_counter', change=self.seat_capacity)
        # Save departure time
        self.arrival_departure_times['aircraft'][aircraft_id]['departure_time'] = self.env.now

    def is_time_overlapping(self, time: float, agent_type: str, tracker: Dict) -> int:
        if agent_type == 'aircraft':
            if len(tracker) == 0:
                return time
            if time not in list(tracker[agent_type].keys()):
                return time
            time += 1/60/60/1000  # add 0.01 milisecond
            return self.is_time_overlapping(time=time, agent_type=agent_type, tracker=tracker)
        elif agent_type == 'passenger':
            if len(tracker) == 0:
                return time
            if time not in list(tracker[agent_type].keys()):
                return time
            time += 1/60/60/1000
            return self.is_time_overlapping(time=time, agent_type=agent_type, tracker=tracker)
        elif agent_type == 'queue':
            if len(tracker) == 0:
                return time
            if time not in list(tracker.keys()):
                return time
            time += 1/60/60/1000
            return self.is_time_overlapping(time=time, agent_type=agent_type, tracker=tracker)
        else:
            raise ValueError('agent_type must be either aircraft, passenger or tracker')          