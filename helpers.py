import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
import time
from datetime import datetime, timedelta
import psycopg2

def plot_output_curve(data: dict, agents: list):
    # Determine the number of agents to set the number of subplots
    num_agents = len(agents)
    fig, axs = plt.subplots(1, num_agents, figsize=(num_agents*5, 4)) # Adjust size as needed
    
    # If there is only one agent, axs will not be an array, so we wrap it in a list
    if num_agents == 1:
        axs = [axs]
    
    for i, agent in enumerate(agents):
        agent_counter = data[agent]
        axs[i].plot(list(agent_counter['arrival_counter'].keys()), list(agent_counter['arrival_counter'].values()), label=f'{agent} arrival', linestyle='--', alpha=0.7)
        axs[i].plot(list(agent_counter['departure_counter'].keys()), list(agent_counter['departure_counter'].values()), label=f'{agent} departure', linestyle='--', alpha=0.7)
        
        axs[i].set_title(f'{agent} Output Curve')
        axs[i].set_xlabel('Time (hr)')
        axs[i].set_xlabel('Cumulative Count')
        axs[i].legend()
        axs[i].grid()
        axs[i].xaxis.set_major_locator(MaxNLocator(integer=True))

    plt.tight_layout() # Adjust layout to not overlap
    plt.show()

def plot_queue_lengths(data: dict, agents: list):
    ax = plt.figure(figsize=(14, 6)).gca()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for agent in agents:
        agent_queue = data[agent]
        ax.plot(list(agent_queue.keys()), list(agent_queue.values()), label=f'{agent}', linestyle='--', alpha=0.7)
        # plt.scatter(list(agent_queue.keys()), list(agent_queue.values()), label=f'{agent}', marker='o', alpha=0.5, s=5)

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title('Queue Lengths')
    ax.set_xlabel('Time (hr)')
    ax.set_xlabel('Queue Length')
    ax.legend()

    ax.grid()
    plt.show()

def plot_rejected_aircraft_counter(data: dict):
    fig, ax = plt.subplots()
    ax.plot(list(data.keys()), list(data.values()), label='Rejected Aircraft')
    # plt.title('Cumulative Number of Rejected Aircraft')
    plt.xlabel('Time (hr)')
    plt.ylabel('Cumulative Number of Rejected Aircraft')
    plt.legend()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid()
    plt.show()

def save_simulation_results_sqlite(db_name, parameters, simulation):
    save_metrics_to_sqlite(db_name,
                           parameters['num_park'], 
                           parameters['aircraft_arrival_rate'], 
                           parameters['passenger_arrival_rate'], 
                           parameters['charge_time'], 
                           parameters['terminal_buffer_capacity'],
                           parameters['blocking'],
                           parameters['seed'],
                           simulation)
    
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_postgres_db(db_name):
    # PostgreSQL superuser credentials and target database/user details
    superuser = 'emin'
    superuser_password = 'emin'
    host = 'localhost'
    your_username = 'your_username'
    your_password = 'your_password'

    # Connect to PostgreSQL server
    conn = psycopg2.connect(dbname='postgres', user=superuser, password=superuser_password, host=host)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    # Cursor to execute commands
    cur = conn.cursor()

    # Create database (skip if exists)
    try:
        cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(db_name)))
        print(f"Database {db_name} created successfully.")
    except psycopg2.errors.DuplicateDatabase:
        print(f"Database {db_name} already exists.")

    # Create user (skip if exists)
    try:
        cur.execute(sql.SQL("CREATE USER {} WITH ENCRYPTED PASSWORD %s;").format(sql.Identifier(your_username)), [your_password])
        print(f"User {your_username} created successfully.")
    except psycopg2.errors.DuplicateObject:
        print(f"User {your_username} already exists.")

    # Grant privileges to the user on the database
    cur.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {};").format(sql.Identifier(db_name), sql.Identifier(your_username)))
    print(f"Granted all privileges on {db_name} to {your_username}.")

    # Close communication with the database
    cur.close()
    conn.close()

def save_simulation_results_postgres(db_name, parameters, system_metrics):
    # If postgres db is not created, create it and give privileges to the user
    # sudo -u postgres psql
    # CREATE DATABASE vertiport_sim;
    # CREATE USER emin WITH ENCRYPTED PASSWORD 'emin';
    # GRANT ALL PRIVILEGES ON DATABASE vertiport_sim TO emin;
    
    # PostgreSQL connection string
    user, password, host, port = 'emin', 'emin', 'localhost', '5432'
    conn_str = f"dbname='{db_name}' user='{user}' password='{password}' host='{host}' port='{port}'"
    
    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Create table if it doesn't exist (adjust the data types as necessary)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS simulation_metrics (
                id SERIAL PRIMARY KEY, 
                tlof_feedback BOOLEAN,
                seed INTEGER, 
                num_park INTEGER, 
                aircraft_arrival_rate INTEGER, 
                passenger_arrival_rate INTEGER, 
                tlof_time REAL,
                charge_time REAL,
                terminal_buffer_capacity REAL, 
                blocking BOOLEAN, 
                num_rejected_aircraft INTEGER,
                aircraft_throughput_rate REAL, 
                terminal_queue_length REAL, 
                avg_num_aircraft_at_surface REAL, 
                passenger_queue_length REAL, 
                variance_in_terminal_queue_length REAL, 
                variance_in_pax_queue_length REAL
            )
        ''')

        # Insert a row
        cur.execute('''
            INSERT INTO simulation_metrics (
                tlof_feedback, seed, num_park, aircraft_arrival_rate, passenger_arrival_rate, tlof_time, charge_time, terminal_buffer_capacity, blocking, num_rejected_aircraft, aircraft_throughput_rate, terminal_queue_length, avg_num_aircraft_at_surface, passenger_queue_length, variance_in_terminal_queue_length, variance_in_pax_queue_length
            ) VALUES (%s, %s, %s, %s, %s, %s ,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            parameters['tlof_feedback'],
            parameters['seed'], 
            parameters['num_park'], 
            parameters['aircraft_arrival_rate'], 
            parameters['passenger_arrival_rate'], 
            parameters['tlof_time'],
            parameters['charge_time'], 
            parameters['terminal_buffer_capacity'], 
            parameters['blocking'], 
            system_metrics.get_rejected_num_aircraft(),
            round(system_metrics.average_aircraft_throughput(),2), 
            round(system_metrics.average_terminal_queue_length(),2), 
            round(system_metrics.average_num_aircraft_at_surface(),2), 
            round(system_metrics.average_passenger_queue_length(),2), 
            round(system_metrics.variance_in_terminal_queue_length(),2), 
            round(system_metrics.variance_in_pax_queue_length(),2)))

        # Commit the transaction
        conn.commit()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            # Close the connection
            conn.close()


def save_metrics_to_sqlite(db_name, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, seed, sim):
    import sqlite3
    conn = sqlite3.connect(f'{db_name}.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, seed INTEGER, num_park INTEGER, aircraft_arrival_rate INTEGER, passenger_arrival_rate INTEGER, charge_time INTEGER, terminal_buffer_capacity REAL, blocking INTEGER, aircraft_throughput_rate REAL, terminal_queue_length REAL, avg_num_aircraft_at_surface REAL, passenger_queue_length REAL, variance_in_terminal_queue_length REAL, variance_in_pax_queue_length REAL)')
    c.execute('INSERT INTO metrics (seed, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, aircraft_throughput_rate, terminal_queue_length, avg_num_aircraft_at_surface, passenger_queue_length, variance_in_terminal_queue_length, variance_in_pax_queue_length) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?)', 
              (seed, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, round(sim.average_aircraft_throughput(),2), round(sim.average_terminal_queue_length(),2), round(sim.average_num_aircraft_at_surface(),2), round(sim.average_passenger_queue_length(),2), round(sim.variance_in_terminal_queue_length(),2), round(sim.variance_in_pax_queue_length(),2)))
    conn.commit()
    conn.close()

def save_metrics_to_postgres(db_name, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, seed, sim):
    # PostgreSQL connection string
    user, password, host, port = 'emin', 'emin', 'localhost', '5432'
    conn_str = f"dbname='{db_name}' user='{user}' password='{password}' host='{host}' port='{port}'"
    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        cur.execute('CREATE TABLE IF NOT EXISTS metrics (id SERIAL PRIMARY KEY, seed INTEGER, num_park INTEGER, aircraft_arrival_rate INTEGER, passenger_arrival_rate INTEGER, charge_time INTEGER, terminal_buffer_capacity REAL, blocking INTEGER, aircraft_throughput_rate REAL, terminal_queue_length REAL, avg_num_aircraft_at_surface REAL, passenger_queue_length REAL, variance_in_terminal_queue_length REAL, variance_in_pax_queue_length REAL)')
        
        # Insert a row
        cur.execute('INSERT INTO metrics (seed, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, aircraft_throughput_rate, terminal_queue_length, avg_num_aircraft_at_surface, passenger_queue_length, variance_in_terminal_queue_length, variance_in_pax_queue_length) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                    (seed, num_park, aircraft_arrival_rate, passenger_arrival_rate, charge_time, terminal_buffer_capacity, blocking, round(sim.average_aircraft_throughput(),2), round(sim.average_terminal_queue_length(),2), round(sim.average_num_aircraft_at_surface(),2), round(sim.average_passenger_queue_length(),2), round(sim.variance_in_terminal_queue_length(),2), round(sim.variance_in_pax_queue_length(),2)))
        
        # Commit the transaction
        conn.commit()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            # Close the connection
            conn.close()


# Pre-generate IDs based on expected numbers
def generate_ids(num_agents, prefix):
    return [f"{prefix}_{i}" for i in range(num_agents)]