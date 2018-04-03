# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 15:29:48 2018

@author: iis519
"""

import numpy as np
#import matplotlib.pyplot as plt
#import librosa
#import soundfile
#import madmom
#import os

import multiprocessing
import psutil
import single_worker as sw
import audio_interface_control as aic
import random

import beat_tracking_util as btu

import time
#from time import gmtime, strftime
#from datetime import datetime
#from scipy.ndimage.filters import maximum_filter

np.seterr(invalid='ignore')


# start operation center process here  
def operation_center(prog_start_time,                     \
                     operation_proc_next_beat,            \
                     operation_proc_next_beat_count,      \
                     operation_proc_bpm,                  \
                     operation_proc_bperiod,              \
                     operation_proc_job_processed,        \
                     operation_proc_cmd_pstop,            \
                     operation_proc_status_ready          \
                     ):
    # operation center function starts here

    # initialize audio interface
    samp_rate = 44100
    sm_audio_data_size = samp_rate * 60 * 3   # space for 5 min long audio 
    
    # create sheared memory for audio interface process
    ai_proc_sm_pstop = multiprocessing.Value('i', 0)
    ai_proc_sm_rec_running = multiprocessing.Value('i', 0)
    ai_proc_sm_data_chunk = multiprocessing.Value('i', 0)
    ai_proc_sm_data_chunk_size = multiprocessing.Value('d', 0)
    ai_proc_sm_data_array_end = multiprocessing.Value('i', 0)
    ai_proc_sm_data_array = multiprocessing.Array('d', sm_audio_data_size)
    #ai_process_sm_data_queue = multiprocessing.Queue()

    ai_process_main = multiprocessing.Process(target = aic.audio_interface_control,  \
                                              args = (ai_proc_sm_pstop,              \
                                                      ai_proc_sm_rec_running,        \
                                                      ai_proc_sm_data_chunk,         \
                                                      ai_proc_sm_data_chunk_size,    \
                                                      ai_proc_sm_data_array_end,     \
                                                      ai_proc_sm_data_array,         \
                                                     )                               \
                                              )
    ai_process_main.daemon = True
    ai_process_main.start()

    # waiting for Rec. process start
    while (ai_proc_sm_rec_running.value == 0):
        time.sleep(0.01)
    print ("[Main Process] audio interface is ready.")
    # audio interface initialized


    ### initialize workers ###
    audio_buffer_len = 10.0
    realtime_audio_array_size = int(samp_rate * audio_buffer_len) # 8 Sec. memory for audio
    cpu_physical_cores = psutil.cpu_count(logical=False)
    num_of_wkrs = max(cpu_physical_cores - 1, 1)

    sm_realtime_audio_i = list(range(num_of_wkrs))
    sm_start_time_i = list(range(num_of_wkrs))
    sm_w_control_run_i = list(range(num_of_wkrs))
    sm_w_control_kill_i = list(range(num_of_wkrs))
    sm_w_control_min_bpm = list(range(num_of_wkrs))
    sm_w_control_max_bpm = list(range(num_of_wkrs))
    sm_estimate_beat_time_o = list(range(num_of_wkrs))
    sm_estimate_beat_count_o = list(range(num_of_wkrs))
    sm_estimate_beat_data_len_o = list(range(num_of_wkrs))
    sm_estimate_beat_calc_time_o = list(range(num_of_wkrs))
    sm_w_status_is_alive_o = list(range(num_of_wkrs))
    sm_w_status_is_idle_o = list(range(num_of_wkrs))
    sm_w_status_job_done_o = list(range(num_of_wkrs))
    sm_w_status_exec_count_o = list(range(num_of_wkrs))
    beat_tracking_process = list(range(num_of_wkrs))
  
    for wkr_idx in range(num_of_wkrs):            
        sm_realtime_audio_i[wkr_idx] = multiprocessing.Array('d', realtime_audio_array_size)
        sm_start_time_i[wkr_idx] = multiprocessing.Value('d', 0)
        sm_w_control_run_i[wkr_idx] = multiprocessing.Value('i', 0)
        sm_w_control_kill_i[wkr_idx] = multiprocessing.Value('i', 0)
        sm_w_control_min_bpm[wkr_idx] = multiprocessing.Value('d', 60)   # min tempo
        sm_w_control_max_bpm[wkr_idx] = multiprocessing.Value('d', 170)  # max tempo
        sm_estimate_beat_time_o[wkr_idx] = multiprocessing.Array('d', 100)
        sm_estimate_beat_count_o[wkr_idx] = multiprocessing.Array('d', 100)
        sm_estimate_beat_data_len_o[wkr_idx] = multiprocessing.Value('i', 0)
        sm_estimate_beat_calc_time_o[wkr_idx] = multiprocessing.Value('d', 0)
        sm_w_status_is_alive_o[wkr_idx] = multiprocessing.Value('i', 0)
        sm_w_status_is_idle_o[wkr_idx] = multiprocessing.Value('i', 0)
        sm_w_status_job_done_o[wkr_idx] = multiprocessing.Value('i', 0)
        sm_w_status_exec_count_o[wkr_idx] = multiprocessing.Value('i', 0)        
        
        # start single worker process here
        beat_tracking_process[wkr_idx] = multiprocessing.Process(target = sw.single_worker,             \
                                                        args = (sm_realtime_audio_i[wkr_idx],           \
                                                                sm_start_time_i[wkr_idx],               \
                                                                sm_w_control_run_i[wkr_idx],            \
                                                                sm_w_control_kill_i[wkr_idx],           \
                                                                sm_w_control_min_bpm[wkr_idx],          \
                                                                sm_w_control_max_bpm[wkr_idx],          \
                                                                sm_estimate_beat_time_o[wkr_idx],       \
                                                                sm_estimate_beat_count_o[wkr_idx],      \
                                                                sm_estimate_beat_data_len_o[wkr_idx],   \
                                                                sm_estimate_beat_calc_time_o[wkr_idx],  \
                                                                sm_w_status_is_alive_o[wkr_idx],        \
                                                                sm_w_status_is_idle_o[wkr_idx],         \
                                                                sm_w_status_job_done_o[wkr_idx],        \
                                                                sm_w_status_exec_count_o[wkr_idx]       \
                                                                )                                       \
                                                        )
        beat_tracking_process[wkr_idx].daemon = True
        beat_tracking_process[wkr_idx].start()
        time.sleep(0.5)

    ########### waiting for all workers ready ##########
    show_refersh = 0.2
    while_loop_runed = 0
    tot_alive_wkrs = 0

    while(tot_alive_wkrs != num_of_wkrs) :
        # check alive worker result
        tot_alive_wkrs = 0
        for x in range(num_of_wkrs) :
            if (sm_w_status_is_alive_o[x].value == 1) :
                tot_alive_wkrs += 1

        # show lateset worker info
        mod_time = (time.time() % show_refersh)
        if (while_loop_runed == 0) :
            if mod_time < (show_refersh * 0.5) :
                #print ("[info] waiting for workers ready : {}/{}".format(tot_alive_wkrs, num_of_wkrs))
                while_loop_runed = 1
        else : # loop already runned , reset loop
            if mod_time > (show_refersh * 0.5) :
                while_loop_runed = 0
            time.sleep(0.01)
    ################################################
    time.sleep(0.1)
    print ("[Main Process] all workers are ready now")



    # waiting for audio interface filling
    buf_time = 10.0

    while (ai_proc_sm_data_array_end.value <= samp_rate * buf_time):
        time.sleep(1.0)
        filled_buffer = ai_proc_sm_data_chunk.value * ai_proc_sm_data_chunk_size.value
        print ("[Main Process] audio interface buffer : {}%".format(int(min(100*float(filled_buffer) / buf_time, 100))))

    print ("[Main Process] audio interface buffer is {:.2f} Sec. now".format(buf_time))


    print ("[Main Process] initialization done")

    # send out ready state
    operation_proc_status_ready.value = 1

    # test process run time
    
    print ("[Main Process] start job calculation speed test")
    
    for wkr_idx in range(num_of_wkrs) :
        sm_w_control_run_i[wkr_idx].value = 1
        time.sleep(1.0)
    
    #time.sleep(3)

    while (operation_proc_cmd_pstop.value == 0):        
        time.sleep(0.01)
        flag = 1
        for wkr_idx in range(num_of_wkrs) :
            if (sm_w_status_job_done_o[wkr_idx].value == 0):
                flag = 0
        if flag == 1:
            break

    # clear job done flag
    for wkr_idx in range(num_of_wkrs) :
        sm_w_status_job_done_o[wkr_idx].value = 0

    print ("[Main Process] job calculation speed test is done")

    # calculate avg calculation time    
    cal_time_sum = 0.0
    cal_time_avg = 0.0
    for wkr_idx in range(num_of_wkrs) :
        cal_time_sum += sm_estimate_beat_calc_time_o[wkr_idx].value
    cal_time_avg = cal_time_sum / float(num_of_wkrs)
    worker_sleep_period = (cal_time_avg / float(num_of_wkrs)) * 1.20 + 0.6
    
    print ("[Main Process] Single beat tracking calculation time : {}".format(cal_time_avg))
    print ("[Main Process] Period between calculation: {}".format(worker_sleep_period))
        

    # create an empty list for saving job    
    job_result_list = []
    saved_job_result = 0
    processed_job = 0
    avg_bprd = 1.0
    
    last_job_exec_time = time.time() - prog_start_time
    
    # run sub process loop here, kill the loop until "operation_proc_cmd_pstop" = 1
    while (operation_proc_cmd_pstop.value == 0):
        time.sleep(0.02)

        # check and update worker status here
        idle_worker_pool = []
        for wkr_idx in range(num_of_wkrs) :
            # check idle workers
            if (sm_w_status_is_idle_o[wkr_idx].value == 1) :
                idle_worker_pool.append(wkr_idx)
            # keep calculated result    
            if (sm_w_status_job_done_o[wkr_idx].value == 1) :
                # clear job status
                sm_w_status_job_done_o[wkr_idx].value = 0
                
                if (sm_estimate_beat_data_len_o < 6): # bad data case
                    pass
                
                else: # good data case
                    start_time_tmp = sm_start_time_i[wkr_idx].value
                    beat_info_beat_tmp = np.array(sm_estimate_beat_count_o[wkr_idx][0 : sm_estimate_beat_data_len_o[wkr_idx].value])
                    beat_info_time_tmp = np.array(sm_estimate_beat_time_o[wkr_idx][0 : sm_estimate_beat_data_len_o[wkr_idx].value])
                
                    job_done_obj = btu.single_job_result()
                    job_done_obj.update_value(start_time_tmp, beat_info_beat_tmp, beat_info_time_tmp)
                    
                    if saved_job_result > 5:

                        step_diff, min_dist = btu.get_beat_step_dif(job_result_list[-1].beat_time_abs_ext[:8], job_done_obj.beat_time_abs_ext[:8], avg_bprd)

                        if step_diff > 12:  # forced update
                            job_result_list.append(job_done_obj)                    
                            saved_job_result = len(job_result_list)
                        else:
                            if (min_dist/avg_bprd < 0.50):  # pick better result
                                job_result_list.append(job_done_obj)
                                saved_job_result = len(job_result_list)
                            else:    # no update
                                pass
                    else:                                             
                        job_result_list.append(job_done_obj)
                        saved_job_result = len(job_result_list)
        # check worker status end here
                                      
        # pick next worker randomly
        if len(idle_worker_pool) > 0:
            next_worker = random.randint(np.min(idle_worker_pool), np.max(idle_worker_pool))
        else : # if no worker available, assign "-1"
            next_worker = -1


        # assign job to next worker here
        if (next_worker > -1) and \
           ( (time.time() - prog_start_time) > (last_job_exec_time + worker_sleep_period) ): # if worker avaliable & wait for sometime
           
            # update lasy job exec time
            last_job_exec_time = (time.time() - prog_start_time)
            
            # put input audio data into worker's shared memory
            try:
                sm_realtime_audio_i[next_worker][0:realtime_audio_array_size] = \
                               ai_proc_sm_data_array[(ai_proc_sm_data_array_end.value-realtime_audio_array_size) : ai_proc_sm_data_array_end.value]
                             
                # save worker run start time into worker
                sm_start_time_i[next_worker].value = time.time() - prog_start_time - audio_buffer_len
                           
                # send "run" cmd to worker
                sm_w_control_run_i[next_worker].value = 1
                sm_w_status_is_idle_o[next_worker].value = 0

            except ValueError:
                pass  
            
        else : # if no worker avaliable
            #print ("[operation process] no idle worker now")
            time.sleep(0.02)
            pass


        # if any new job is done, do something here
        while (processed_job < saved_job_result):
                                                   
            operation_proc_job_processed.value = saved_job_result
            
            pridicted_beat_num = 48

            if saved_job_result < 6:
                operation_proc_next_beat[0:pridicted_beat_num] = job_result_list[-1].beat_time_abs_ext[0:pridicted_beat_num]
                operation_proc_bpm.value = job_result_list[-1].bpm
                operation_proc_bperiod.value = job_result_list[-1].beat_period_avg
            else:
                end_idx = saved_job_result - 1

                avg_num = 6

                avg_bprd = btu.get_avg_beat_period(job_result_list, end_idx, avg_num)

                beat_step_diff_acc, beat_step_dif, beat_step_diff_min = \
                                btu.get_beat_step_dif_list(job_result_list, avg_bprd, end_idx, avg_num)

                predicted_beat_time, predicted_beat_count = \
                                btu.get_avg_time_beat(job_result_list, beat_step_diff_acc, end_idx, pridicted_beat_num)

                operation_proc_bperiod.value = avg_bprd
                operation_proc_bpm.value = 60.0 / avg_bprd
                
                #print (predicted_beat_time)
                operation_proc_next_beat[0:pridicted_beat_num] = predicted_beat_time[0:pridicted_beat_num] #predicted_beat_time[0:pridicted_beat_num]
                operation_proc_next_beat_count[0:pridicted_beat_num] = predicted_beat_count[0:pridicted_beat_num]
                
                  
            processed_job += 1            
    # sub process loop end here

    
    # stop audio interface process
    ai_proc_sm_pstop.value = 1
   
    # stop all workers process
    for wkr_idx in range(num_of_wkrs) :
        if (sm_w_status_is_alive_o[wkr_idx].value == 1) :
            sm_w_control_kill_i[wkr_idx].value = 1
        time.sleep(0.05)
    time.sleep(0.05)
        
    print ("[Main Process] Main process end")
# operation center ends here





if __name__ == '__main__':
    # save start time
    prog_start_time = time.time() 
    elapse_time = time.time() - prog_start_time
    
    print ("[Main Process] main program starts run here...")
    operation_proc_cmd_pstop = multiprocessing.Value('i', 0)
    operation_proc_status_ready = multiprocessing.Value('i', 0)
    operation_proc_next_beat = multiprocessing.Array('d', 48)
    operation_proc_next_beat_count = multiprocessing.Array('d', 48)
    operation_proc_bpm = multiprocessing.Value('d', 72)
    operation_proc_bperiod = multiprocessing.Value('d', 1.0)
    operation_proc_job_processed = multiprocessing.Value('i', 0)
    
    # start operation process here    
    operation_center_proc = multiprocessing.Process(target = operation_center,                 \
                                                    args = (prog_start_time,                   \
                                                            operation_proc_next_beat,       \
                                                            operation_proc_next_beat_count, \
                                                            operation_proc_bpm,                \
                                                            operation_proc_bperiod,            \
                                                            operation_proc_job_processed,      \
                                                            operation_proc_cmd_pstop,          \
                                                            operation_proc_status_ready,       \
                                                            )                                  \
                                                    )
    #operation_center_proc.daemon = True
    operation_center_proc.start()

    #print ("[Main Process] waiting for sub process ready")
    while (1):
        time.sleep(0.5)
        #print ("[main info] waiting for sub process ready")                              
        if (operation_proc_status_ready.value == 1):
            break

    print ("[Main Process] sub process is ready now")


    # wait client set out result
    print ("[Main Process] waiting for client ready.")    
    while (1):
        if (operation_proc_job_processed.value != 0):
            time.sleep(0.01)
            break
    print ("[Main Process] client ready to send result.")



    loop_run_time = 90.0
    
    refresh_loop_execed = 0
    refresh_period = 0.001
    beat_counted = 0
    latest_count_time = 0.0
        
    #client_ready_start_time = time.time()
    client_t_offset = time.time() - prog_start_time
    print ("[Main Process] main prog start count and wait")
    
    while (True):                                       
        while_elapse_time = (time.time() - prog_start_time - client_t_offset)
        
        # show information every "refresh_period" Sec.
        mod_time = (while_elapse_time % refresh_period)
        if (refresh_loop_execed == 0) :
            if mod_time < (refresh_period * 0.50) :
                
                latest_beat_array = np.array(operation_proc_next_beat[0:32]) - client_t_offset
                
                latest_bpm = operation_proc_bpm.value
                latest_bprd = operation_proc_bperiod.value
                
                job_num = operation_proc_job_processed.value                
                
                t_offset = 0.20
                time_diff_pos = while_elapse_time + t_offset - latest_beat_array
                time_diff_pos = np.min(time_diff_pos[time_diff_pos>0])
                
                beat_idx = np.argmin(np.abs(time_diff_pos))
                
                if (time_diff_pos < latest_bprd*0.50):
                    if (beat_counted == 0):
                        latest_count_time = while_elapse_time
                        beat_counted = 1
                        
                        pos = np.argmin(np.abs(latest_count_time - latest_beat_array))
                        beat_now = int(operation_proc_next_beat_count[pos])
                        
                        if (beat_now == 1):
                            print ("Time: {:.2f}, \t BPM={:.1f} \t <======== First Beat".format(while_elapse_time, latest_bpm))
                        else :
                            print ("Time: {:.2f}, \t BPM={:.1f}".format(while_elapse_time, latest_bpm))

                else:
                    if while_elapse_time > (latest_count_time + latest_bprd*0.40):
                        beat_counted = 0                

                refresh_loop_execed = 1
        else : # loop already runned , reset loop
            if mod_time > (refresh_period * 0.50) :
                refresh_loop_execed = 0
            
            # A count down clock to jump out the while loop
            if (while_elapse_time > loop_run_time):      
                break
                
            time.sleep(0.005)
                
        
    # main while loop end here

    print ("[Main Process] main while loop end")

    # kill seb program
    print ("[Main Process] kill operation process")
    operation_proc_cmd_pstop.value = 1
    
    print ("[Main Process] main prog end")






























