# -*- coding: utf-8 -*-
"""
Created on Tue Jan 09 13:42:20 2018

@author: iis519
"""
import numpy as np
#import matplotlib.pyplot as plt
import librosa
#import soundfile
import madmom
#import os, 
import time
import multiprocessing

#from time import gmtime, strftime
#from datetime import datetime
#from scipy.ndimage.filters import maximum_filter

np.seterr(invalid='ignore')

# define single worker here
def single_worker(sm_realtime_audio_i,                 \
                  sm_start_time_i,                     \
                  sm_w_control_run_i,                  \
                  sm_w_control_kill_i,                 \
                  sm_w_control_min_bpm,                \
                  sm_w_control_max_bpm,                \
                  sm_estimate_beat_time_o,             \
                  sm_estimate_beat_count_o,            \
                  sm_estimate_beat_data_len_o,         \
                  sm_estimate_beat_calc_time_o,        \
                  sm_w_status_is_alive_o,              \
                  sm_w_status_is_idle_o,               \
                  sm_w_status_job_done_o,              \
                  sm_w_status_exec_count_o             \
                  ) :
    
    # process is running, set running flag = 1
    sm_w_status_is_alive_o.value = 1
    sm_w_status_is_idle_o.value = 1
    sm_w_status_job_done_o.value = 0
    sm_w_status_exec_count_o.value = 0
    
    print ("[single worker] single worker is initialized.")
    
    while(sm_w_control_kill_i.value == 0) :
        
        # no need to run job, stay idle
        if (sm_w_control_run_i.value == 0):           
            time.sleep(0.01)
            pass
        
        # run real-time job here
        else : 
            start_time = time.time()
            
            sm_w_status_is_idle_o.value = 0
            
            act = madmom.features.beats.RNNDownBeatProcessor(fps=100)( np.asarray(sm_realtime_audio_i[:]) )

            min_bpm_input = sm_w_control_min_bpm.value
            max_bpm_input = sm_w_control_max_bpm.value

            #proc = madmom.features.DBNDownBeatTrackingProcessor(beats_per_bar=[2, 3, 4],   \
            proc = madmom.features.DBNDownBeatTrackingProcessor(beats_per_bar=[4],         \
                                                                fps=100,                   \
                                                                min_bpm=min_bpm_input,     \
                                                                max_bpm=max_bpm_input
                                                                )
            
            '''
            act = madmom.features.RNNBeatProcessor(fps=100)(np.asarray(sm_realtime_audio_i[:]))
            proc = madmom.features.BeatDetectionProcessor(fps=100)
            '''

            beat_calc_result = proc(act)
            
            beat_calc_len = len(beat_calc_result)
            
            sm_estimate_beat_data_len_o.value = beat_calc_len
            sm_estimate_beat_time_o[0: beat_calc_len] = beat_calc_result[:, 0]
            sm_estimate_beat_count_o[0: beat_calc_len] = beat_calc_result[:, 1]
            
            elapsed_time = time.time() - start_time
                                    
            sm_estimate_beat_calc_time_o.value = elapsed_time

            sm_w_status_exec_count_o.value += 1
            sm_w_control_run_i.value = 0
            sm_w_status_is_idle_o.value = 1
            sm_w_status_job_done_o.value = 1
                
        # run real-time job end here
        
    # single worker while loop end here
    
    sm_w_status_is_alive_o.value = 0
    print ("[single worker] all single workers are killed.")

    # single worker process end here

if __name__ == '__main__':
    
    abs_system_time = time.time()
    
    audio_target = "data\\Drum_simple_1_mono.wav"
    
    samp_rate = 44100
    
    signal_sf, sample_rate_sf = librosa.load(audio_target, mono=True, sr=samp_rate)
    
    realtime_audio_array_size = int(samp_rate * 8.0)
    
    sm_realtime_audio_i = multiprocessing.Array('d', realtime_audio_array_size)
    sm_start_time_i = multiprocessing.Value('d', 0)
    sm_w_control_run_i = multiprocessing.Value('i', 0)
    sm_w_control_kill_i = multiprocessing.Value('i', 0)
    sm_estimate_beat_time_o = multiprocessing.Array('d', 100)
    sm_estimate_beat_count_o = multiprocessing.Array('d', 100)
    sm_estimate_beat_data_len_o = multiprocessing.Value('i', 0)
    sm_estimate_beat_calc_time_o = multiprocessing.Value('d', 0)
    sm_w_status_is_alive_o = multiprocessing.Value('i', 0)
    sm_w_status_is_idle_o = multiprocessing.Value('i', 0)
    sm_w_status_job_done_o = multiprocessing.Value('i', 0)
    sm_w_status_exec_count_o = multiprocessing.Value('i', 0)
    

    beat_tracking_process = multiprocessing.Process(target = single_worker,                \
                                                    args = (sm_realtime_audio_i,           \
                                                            sm_start_time_i,               \
                                                            sm_w_control_run_i,            \
                                                            sm_w_control_kill_i,           \
                                                            sm_estimate_beat_time_o,       \
                                                            sm_estimate_beat_count_o,      \
                                                            sm_estimate_beat_data_len_o,   \
                                                            sm_estimate_beat_calc_time_o,  \
                                                            sm_w_status_is_alive_o,        \
                                                            sm_w_status_is_idle_o,         \
                                                            sm_w_status_job_done_o,        \
                                                            sm_w_status_exec_count_o       \
                                                            )                              \
                                                    )
    beat_tracking_process.daemon = True
    beat_tracking_process.start()
    
    # waiting side process init.
    while (sm_w_status_is_alive_o.value == 0):
        time.sleep(0.5)
        
    print ("single process is initialized")
    
    print ("run : {}".format(sm_w_control_run_i.value))
    print ("kill : {}".format(sm_w_control_kill_i.value))
    print ("alive : {}".format(sm_w_status_is_alive_o.value))    
    print ("idle : {}".format(sm_w_status_is_idle_o.value))    
    print ("jdone : {}".format(sm_w_status_job_done_o.value))
    print ("jcnt : {}".format(sm_w_status_exec_count_o.value))
     
    
    sm_realtime_audio_i[0:realtime_audio_array_size] = signal_sf[0:realtime_audio_array_size]
    
    # start run job
    sm_w_control_run_i.value = 1

    print ("job 1 start")

    print ("run : {}".format(sm_w_control_run_i.value))
    print ("kill : {}".format(sm_w_control_kill_i.value))
    print ("alive : {}".format(sm_w_status_is_alive_o.value))    
    print ("idle : {}".format(sm_w_status_is_idle_o.value))    
    print ("jcnt : {}".format(sm_w_status_exec_count_o.value))  
    
    while (sm_w_status_job_done_o.value == 0):
        time.sleep(0.5)  
        print ("waiting for job 1 calculation")
        #print ("run : {}".format(sm_w_control_run_i.value))
        #print ("kill : {}".format(sm_w_control_kill_i.value))
        #print ("alive : {}".format(sm_w_status_is_alive_o.value))    
        #print ("idle : {}".format(sm_w_status_is_idle_o.value))    
        #print ("jexec : {}".format(sm_w_status_exec_count_o.value))  
    
    print ("job 1 done")

    print ("run : {}".format(sm_w_control_run_i.value))
    print ("kill : {}".format(sm_w_control_kill_i.value))
    print ("alive : {}".format(sm_w_status_is_alive_o.value))    
    print ("idle : {}".format(sm_w_status_is_idle_o.value))    
    print ("jcnt : {}".format(sm_w_status_exec_count_o.value))  


    print ("check value")

    print (sm_estimate_beat_data_len_o.value)       
    print (sm_estimate_beat_time_o[:sm_estimate_beat_data_len_o.value])
    print (sm_estimate_beat_count_o[:sm_estimate_beat_data_len_o.value])
    print (sm_estimate_beat_calc_time_o.value)
    print (sm_w_status_exec_count_o.value)


    sm_realtime_audio_i[0:realtime_audio_array_size] = signal_sf[44100:realtime_audio_array_size+44100]

    sm_w_status_job_done_o.value = 0
    sm_w_control_run_i.value = 1


    print ("job 2 start")

    print ("run : {}".format(sm_w_control_run_i.value))
    print ("kill : {}".format(sm_w_control_kill_i.value))
    print ("alive : {}".format(sm_w_status_is_alive_o.value))    
    print ("idle : {}".format(sm_w_status_is_idle_o.value))    
    print ("jcnt : {}".format(sm_w_status_exec_count_o.value))  
    
    while (sm_w_status_job_done_o.value == 0):
        time.sleep(0.5)
        print ("waiting for job 2 calculation")
        #print ("run : {}".format(sm_w_control_run_i.value))
        #print ("kill : {}".format(sm_w_control_kill_i.value))
        #print ("alive : {}".format(sm_w_status_is_alive_o.value))    
        #print ("idle : {}".format(sm_w_status_is_idle_o.value))    
        #print ("jexec : {}".format(sm_w_status_exec_count_o.value))  
    
    print ("job 2 done")

    print ("run : {}".format(sm_w_control_run_i.value))
    print ("kill : {}".format(sm_w_control_kill_i.value))
    print ("alive : {}".format(sm_w_status_is_alive_o.value))    
    print ("idle : {}".format(sm_w_status_is_idle_o.value))    
    print ("jcnt : {}".format(sm_w_status_exec_count_o.value))  


    print ("check value")

    print (sm_estimate_beat_data_len_o.value)       
    print (sm_estimate_beat_time_o[:sm_estimate_beat_data_len_o.value])
    print (sm_estimate_beat_count_o[:sm_estimate_beat_data_len_o.value])
    print (sm_estimate_beat_calc_time_o.value)
    print (sm_w_status_exec_count_o.value)








    
    
    sm_w_control_kill_i.value = 1
    
    time.sleep(0.1)
    
    print ("main program end here\n")










