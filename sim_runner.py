import itertools
from multiprocessing import Pool
import numpy as np
import psycopg2
import tqdm
from helpers import save_simulation_results_postgres
from vertiport_sim import VertiportSimulation
from helpers import generate_ids
import simpy
from metrics import SystemMetrics


aircraft_arrival_rates =  list(range(1, 41, 1))
passenger_arrival_rates = [10000]
charge_rates = np.array([5, 10, 15, 20, 25, 30]) # minutes
charge_times = 60/charge_rates
num_parks = [1,2,3,4,5,6,7,8,9,10]
num_aircraft = [2500]
num_passenger = [10000]
seat_capacity = [4]
tlof_feedback = [False]
tlof_times = [1] # minutes
stochastic = [True]
blocking = [True]
no_pax_arrival = [True]
terminal_buffer_capacity = [50]
seed = list(range(0, 30))


def run_simulation(aircraft_arrival_rate, 
                   passenger_arrival_rate, 
                   charge_time, 
                   num_park, 
                   num_aircraft, 
                   num_passenger, 
                   seat_capacity, 
                   tlof_feedback,
                   tlof_time, 
                   stochastic, 
                   blocking, 
                   terminal_buffer_capacity,
                   seed,
                   no_pax_arrival,
                   is_logging=False):
    parameters = {
        'aircraft_arrival_rate': aircraft_arrival_rate,
        'passenger_arrival_rate': passenger_arrival_rate,
        'charge_time': charge_time,
        'num_park': num_park,
        'num_aircraft': num_aircraft,
        'num_passenger': num_passenger,
        'seat_capacity': seat_capacity,
        'tlof_feedback': tlof_feedback,
        'tlof_time': tlof_time,
        'tlof_feedback': tlof_feedback,
        'stochastic': stochastic,
        'blocking': blocking,
        'terminal_buffer_capacity': terminal_buffer_capacity,
        'no_pax_arrival': no_pax_arrival,
        'seed': seed
    }
    env = simpy.Environment()
    aircraft_mean_interarrival_time = 1/aircraft_arrival_rate # inter-arrival time in hours
    passenger_mean_interarrival_time = 1/passenger_arrival_rate # inter-arrival time in hours
    tlof_mean_service_time = tlof_time/60 # TLOF service time in hours
    charge_mean_service_time = charge_time/60 # Park service time in hours

    aircraft_ids = generate_ids(num_aircraft, "Aircraft")
    passenger_ids = generate_ids(num_passenger, "Passenger")
    termination_event = env.event()
    simulation = VertiportSimulation(env=env, 
                                     aircraft_ids=aircraft_ids, 
                                     passenger_ids=passenger_ids, 
                                     num_park=num_park,
                                     aircraft_mean_interarrival_time=aircraft_mean_interarrival_time, 
                                     passenger_mean_interarrival_time=passenger_mean_interarrival_time, 
                                     tlof_mean_service_time=tlof_mean_service_time, 
                                     charge_mean_service_time=charge_mean_service_time,
                                     seat_capacity=seat_capacity,
                                     termination_event=termination_event,
                                     tlof_feedback=tlof_feedback,
                                     stochastic=stochastic,
                                     blocking=blocking,
                                     terminal_buffer_capacity=terminal_buffer_capacity,
                                     is_logging=is_logging,
                                     no_pax_arrival=no_pax_arrival,
                                     seed=seed)
    if not no_pax_arrival:
        env.process(simulation.passenger_process())
    env.process(simulation.aircraft_arrival_process())
    env.run(until=termination_event)
    system_metrics = SystemMetrics(simulation)
    return parameters, system_metrics

def run_simulation_with_params(params):
    # Unpack your parameters
    aircraft_arrival_rate, passenger_arrival_rate, charge_time, num_park, num_aircraft, num_passenger, seat_capacity, tlof_feedback, tlof_time, stochastic, blocking, terminal_buffer_capacity, no_pax_arrival, seed = params

    # Check if 60/charge_time*num_park is less than aircraft_arrival_rate
    if 60 / charge_time * num_park < aircraft_arrival_rate:
        # Skip this set of parameters
        return
        
    parameters, system_metrics = run_simulation(
        aircraft_arrival_rate=aircraft_arrival_rate,
        passenger_arrival_rate=passenger_arrival_rate,
        charge_time=charge_time,
        num_park=num_park,
        num_aircraft=num_aircraft,
        num_passenger=num_passenger,
        seat_capacity=seat_capacity,
        tlof_feedback=tlof_feedback,
        tlof_time=tlof_time,
        stochastic=stochastic,
        blocking=blocking,
        terminal_buffer_capacity=terminal_buffer_capacity,
        no_pax_arrival=no_pax_arrival,
        is_logging=False,
        seed=seed
    )
    
    # Save the simulation results to the PostgreSQL database
    save_simulation_results_postgres("queueing_sim", parameters=parameters, system_metrics=system_metrics)

if __name__ == "__main__":
    # Generate all possible combinations of the parameters
    parameter_combinations = list(itertools.product(aircraft_arrival_rates, 
                                                    passenger_arrival_rates, 
                                                    charge_times, 
                                                    num_parks, 
                                                    num_aircraft, 
                                                    num_passenger, 
                                                    seat_capacity, 
                                                    tlof_feedback,
                                                    tlof_times, 
                                                    stochastic, 
                                                    blocking, 
                                                    terminal_buffer_capacity, 
                                                    no_pax_arrival,
                                                    seed))

    # Initialize a pool of processes
    with Pool(processes=14) as pool:
        # Use tqdm to show progress
        for _ in tqdm.tqdm(pool.imap_unordered(run_simulation_with_params, parameter_combinations), total=len(parameter_combinations)):
            pass
