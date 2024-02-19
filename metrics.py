from typing import Dict

class SystemMetrics:
    """
    Class to compute performance metrics.
    """
    def __init__(self, sim_object):
        self.sim = sim_object

    def average_aircraft_throughput(self):
        """
        Computes the average hourly aircraft departure rate.
        """
        return list(self.sim.arrival_departure_counter['aircraft']['departure_counter'].values())[-1] / self.sim.env.now
    
    def average_terminal_queue_length(self):
        """
        Computes the average hourly terminal queue length.
        """
        return self.calculate_time_average(self.sim.queue_lengths['aircraft_arrival_queue'])
    
    def average_num_aircraft_at_surface(self):
        """
        Computes the average number of aircraft at the surface.
        """
        return self.calculate_time_average(self.sim.surface_aircraft_count)
    
    def average_passenger_queue_length(self):
        """
        Computes the average number of passengers in the system.
        """
        return self.calculate_time_average(self.sim.queue_lengths['passenger_service_queue'])
    
    def variance_in_terminal_queue_length(self):
        """
        Computes the variance in terminal queue length.
        """
        return self.calculate_variance(self.sim.queue_lengths['aircraft_arrival_queue'])
    
    def variance_in_num_aircraft_at_surface(self):
        """
        Computes the variance in the number of aircraft at the surface.
        """
        return self.calculate_variance(self.sim.surface_aircraft_count)
    
    def variance_in_pax_queue_length(self):
        """
        Computes the variance in the number of passengers in the system.
        """
        return self.calculate_variance(self.sim.queue_lengths['passenger_service_queue'])
    
    def get_rejected_num_aircraft(self):
        """
        Returns the number of rejected aircraft.
        """
        return self.sim.rejected_aircraft_counter

    
    # def calculate_time_average(self, tracker: Dict) -> float:
    #     # Compute the time difference between each consecutive key and multiply by the value. then sum everything and divide by the total time
    #     total_weighted = 0
    #     keys = list(tracker.keys())  # Extracting the keys as a list for direct access

    #     # Calculating total weighted queue more efficiently
    #     for i in range(len(keys) - 1):
    #         duration = keys[i+1] - keys[i]  # Duration between current and next timestamp
    #         queue_length = tracker[keys[i]]  # Current queue length
    #         total_weighted += queue_length * duration

    #     # The total time calculation remains the same
    #     total_time_efficient = keys[-1] - keys[0]

    #     # Calculating the average queue length more efficiently
    #     return total_weighted / total_time_efficient     
    

    def calculate_time_average(self, tracker: Dict) -> float:
        keys = list(tracker.keys())  # Assuming keys are sorted and represent hours

        # Find the index for the key immediately after the first two hours
        start_index = 0
        for i, key in enumerate(keys):
            if key - keys[0] > 5:  # Direct comparison in hours
                start_index = i
                break

        # Ensure there's at least one interval after excluding the first several hours
        if start_index == len(keys) - 1:
            return 0  # Return 0 or suitable value if there's no data to compute average

        # Adjust calculation to start from the key after the first two hours
        total_weighted = 0
        for i in range(start_index, len(keys) - 1):
            duration = keys[i+1] - keys[i]
            queue_length = tracker[keys[i]]
            total_weighted += queue_length * duration

        # Adjust total time calculation to exclude the first two hours
        total_time_adjusted = keys[-1] - keys[start_index]

        # Return the average queue length excluding the first two hours
        return total_weighted / total_time_adjusted if total_time_adjusted != 0 else 0    

    # def calculate_variance(self, tracker: Dict) -> float:
    #     time_average = self.calculate_time_average(tracker)
    #     total_variance = 0
    #     keys = list(tracker.keys())
    #     for i in range(len(keys) - 1):
    #         duration = keys[i+1] - keys[i]
    #         queue_length = tracker[keys[i]]
    #         total_variance += (queue_length - time_average)**2 * duration
    #     total_time = keys[-1] - keys[0]
    #     return total_variance / total_time
    
    def calculate_variance(self, tracker: Dict) -> float:
        # First, ensure the average excludes the first two hours
        time_average = self.calculate_time_average(tracker)
        
        keys = list(tracker.keys())
        
        # Find the start index after the first two hours
        start_index = 0
        for i, key in enumerate(keys):
            if key - keys[0] > 5:  # Using hours directly for comparison
                start_index = i
                break
        
        # Check to ensure there's data to compute after the first two hours
        if start_index == len(keys) - 1:
            return 0  # Return 0 or suitable value if there's no data to compute variance
        
        total_variance = 0
        for i in range(start_index, len(keys) - 1):
            duration = keys[i+1] - keys[i]
            queue_length = tracker[keys[i]]
            total_variance += (queue_length - time_average)**2 * duration
        
        # Adjust total time calculation to exclude the first two hours
        total_time_adjusted = keys[-1] - keys[start_index]
        
        return total_variance / total_time_adjusted if total_time_adjusted != 0 else 0
