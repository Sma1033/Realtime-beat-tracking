import numpy as np
#import random
#import os, sys
#import dill
#import IPython
#import datetime, time
#from datetime import datetime
#from time import gmtime, strftime

# Load MIR Libries
#import librosa            # MIR library
#import madmom             # MIR Library
#import pydub              # MIR Library


# find next 36 beat extended array
def ext_beat_array(base_array, base_array_beat, beat_period):
    start_time = (np.mean(base_array[-4:])) + beat_period * 1.5
    end_time = start_time + beat_period * 82
    beat_array_tmp = np.arange(start_time, end_time, beat_period)
    ext_beat_array_time = beat_array_tmp[0:80]
    
    ary_len = 80
    # fill in beat count information
    ext_beat_array_beat = np.zeros(ary_len).astype(np.int)
    start_beat = np.int(base_array_beat[-1])
    for x in range(0, ary_len):
        if x == 0:
            ext_beat_array_beat[x] = start_beat
        else:
            ext_beat_array_beat[x] = ext_beat_array_beat[x-1] + 1
            if ext_beat_array_beat[x] == 5:
                ext_beat_array_beat[x] -= 4
            
    return ext_beat_array_time, ext_beat_array_beat
    
    
# define beat object to save madmom result
class single_job_result():
    def __init__(self):
        #self.saving_time = 0
        self.job_start_time = 0
        self.beat_data_len = 0
        self.use_last_n_beat = 8
        self.data_is_valid = False
        self.beat_time = []
        self.beat_time_abs = []
        self.beat_time_abs_ext = []
        self.beat_count = []
        self.beat_count_ext = []
        self.beat_period_avg = 0 
        self.bpm = 0
        self.job_calc_time = 0
        
    def update_value(self, start_time, beat_info_beat, beat_info_time):
            self.job_start_time = start_time
            self.beat_data_len = len(beat_info_time)

            self.data_is_valid = (self.beat_data_len >= self.use_last_n_beat)
            
            self.beat_time = beat_info_time[-self.use_last_n_beat:]
            self.beat_time_abs = self.beat_time + self.job_start_time
            self.beat_count = beat_info_beat[-self.use_last_n_beat:]

            tmp_beat_period_list = self.beat_time[1:] - self.beat_time[:-1]
            self.beat_period_avg = np.median(tmp_beat_period_list)
            self.bpm = 60.0 / self.beat_period_avg
    
            temp_time_array, temp_beat_array = ext_beat_array(self.beat_time_abs,
                                                              self.beat_count, 
                                                              self.beat_period_avg)
    
            self.beat_time_abs_ext = temp_time_array
            self.beat_count_ext = temp_beat_array
            
            
            
# calculate average beat period across beat_info obj.
def get_avg_beat_period(input_binf_list, end_idx, avg_num):    
    tmp_beat_perid = 0.0    
    for x in range(0, avg_num):
        tmp_beat_perid += input_binf_list[end_idx-x].beat_period_avg
        #print (input_binf_list[end_idx-x].beat_period_avg)
        
    result = tmp_beat_perid / float(avg_num)
    return result


    
def get_beat_step_dif(matrix_input, matrix_base, beat_value):
    beat_dist = 0
    
    for _ in range(0, 100):
        dist_mid = np.mean(np.abs(matrix_input + beat_dist*beat_value - matrix_base))
        dist_add_beat = np.mean(np.abs(matrix_input + beat_value + beat_dist*beat_value - matrix_base))
        dist_sub_beat = np.mean(np.abs(matrix_input - beat_value + beat_dist*beat_value - matrix_base))    
    
        if (dist_mid <= dist_sub_beat ) and (dist_mid <= dist_add_beat): # right position
            #print (dist_sub_beat/beat_value, dist_mid/beat_value, dist_add_beat/beat_value)
            
            minumum_distance = dist_mid/float(beat_value)
            
            return  (beat_dist, minumum_distance)
        else: # not fit, do some shift
            if dist_add_beat > dist_sub_beat:
                #print("no hit, ++")
                beat_dist -= 1
            else:
                #print("no hit, --")
                beat_dist += 1 
                
                
                
                
def get_beat_step_dif_list(input_binf_list, bprd, end_idx, get_num):

    beat_step_dif_list_acc = []
    beat_step_dif_list_acc.append(0)
    beat_step_dif_list = []
    beat_closest_dist_list = []

    beat_step_dif_list.append(0)
    beat_closest_dist_list.append(0.0)
    
    for x in range(0, get_num-1):
        former_array = input_binf_list[end_idx-x-1].beat_time_abs_ext[0:8]
        latter_array = input_binf_list[end_idx-x].beat_time_abs_ext[0:8]
        beat_step, min_dist = get_beat_step_dif(former_array, latter_array, bprd)

        beat_step_dif_list.append(beat_step)
        beat_closest_dist_list.append(min_dist)
        
        beat_step_dif_list_acc.append(np.sum(beat_step_dif_list))
        
    return (beat_step_dif_list_acc, beat_step_dif_list, beat_closest_dist_list)



def get_avg_time_beat(binf_obj_list, beat_step_acc, end_idx, pridicted_beat_num):
    exp_beat_num = pridicted_beat_num

    list_len = len(beat_step_acc)
    tmp_bcount_array = np.zeros(list_len).astype(np.int)

    for x in range (0, list_len):
        if x == 0 :
            sfifted_beat_n = beat_step_acc[x]
            stacked_btime_matrix = binf_obj_list[end_idx-x].beat_time_abs_ext[0+sfifted_beat_n : exp_beat_num+sfifted_beat_n]
            tmp_bcount_array[x] = binf_obj_list[end_idx-x].beat_count_ext[sfifted_beat_n]
        else:
            sfifted_beat_n = beat_step_acc[x]
            
            try:
                stacked_btime_matrix = np.vstack ([stacked_btime_matrix, 
                                                   binf_obj_list[end_idx-x].beat_time_abs_ext[0+sfifted_beat_n : exp_beat_num+sfifted_beat_n]])
            except ValueError:
                pass
            
            tmp_bcount_array[x] = binf_obj_list[end_idx-x].beat_count_ext[sfifted_beat_n]              

    avg_ext_beat_matrix = np.mean(stacked_btime_matrix, axis=0)

    bcount_mix = np.hstack([tmp_bcount_array, np.array([1,2,3,4])])
    belements, bcounts = np.unique(bcount_mix, return_counts=True)
    first_bcount = np.int(belements[np.argmax(bcounts)])

    final_bcount_array = np.zeros(exp_beat_num).astype(np.int)
    start_beat = first_bcount
    for x in range(0, exp_beat_num):
        if x == 0:
            final_bcount_array[x] = start_beat
        else:
            final_bcount_array[x] = final_bcount_array[x-1] + 1
            if final_bcount_array[x] == 5:
                final_bcount_array[x] -= 4
    
    return (avg_ext_beat_matrix, final_bcount_array)    