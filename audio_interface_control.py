"""
Created on Thu Jul 13 00:23:37 2017 @ author: Sma1033
use this function to find bast match local dtw path
"""
#import Tkinter
import numpy as np
import time
from datetime import datetime
#import os, dill, ast
import multiprocessing
#import threading
#import dtw_job_control as djc
#import ast
import pyaudio, wave
import librosa



def save_wave_16bit(data, file_name, rate):
    # get the max value of int16 data
    max_v = np.iinfo(np.int16).max
    # convert float data into int16 format for saving
    librosa.output.write_wav(file_name,  (data * max_v).astype(np.int16), rate)


class record_service():
    def __init__(self):   
        self.saved_sampling_data = []
        self.saved_sampling_data_str = []
        self.saved_sampling_frame = 0
        self.sync_saved_sampling_frame = 0
        self.SAMPLING_WINDOW = 0.020 # sampling chunk size = 20 ms
        self.SAMPLING_CHANNELS = 1
        self.SAMPLING_RATE = 44100
        self.MONITORING_SAMPLING_INPUT = False #False
        self.NUM_SAMPLES = np.int(self.SAMPLING_RATE * np.float(self.SAMPLING_WINDOW))
        self.pyaud = pyaudio.PyAudio()
        self.sampling_is_running = False
        
        #print "recording service is initialized."        

    def save_wave_file(self, filename, save_data): 
        self.wf = wave.open(filename, 'wb') 
        self.wf.setnchannels(self.SAMPLING_CHANNELS) 
        self.wf.setsampwidth(2) 
        self.wf.setframerate(self.SAMPLING_RATE) 
        self.wf.writeframes("".join(save_data)) 
        self.wf.close()
        print "file:", filename, "is saved."

    def callback(self, in_data, frame_count, time_info, status):
        #global saved_sampling_frame
        self.saved_sampling_frame += 1
        self.saved_sampling_data.append(in_data)
        self.saved_sampling_data_str.append( np.fromstring(in_data, dtype=np.int16) )

        return (in_data, pyaudio.paContinue)

    def run_sampling_stream(self):
        #global sampling_is_running
        if (self.sampling_is_running == False):
            self.audio_stream = self.pyaud.open(format=pyaudio.paInt16,
                                                channels=self.SAMPLING_CHANNELS,
                                                rate=self.SAMPLING_RATE,
                                                input=True,
                                                output=self.MONITORING_SAMPLING_INPUT,
                                                frames_per_buffer=self.NUM_SAMPLES,
                                                stream_callback=self.callback)
            self.audio_stream.start_stream()
            self.sampling_is_running = True
            print "[audio interface] Start recording."
        else:    
            print "[audio interface] Recording is already running"

        #self.recording_service_update()
        #print "sampling is Started."

    def close_sampling_stream(self): 
        #global sampling_is_running
        if (self.sampling_is_running == True):
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.pyaud.terminate()
            self.sampling_is_running = False
            print "[audio interface] Audio frame saved : {0}".format(self.saved_sampling_frame)
            print "[audio interface] Stop recording."
#        else:
#            print "Recording is already stopped"

    def save_data_2_file(self):
        if len(self.saved_sampling_data) > 0:
            filename = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".wav" 
            self.save_wave_file(filename, self.saved_sampling_data)


    def update_frame_array(self,
                           ai_process_sm_data_chunk,
                           ai_process_sm_data_array_end,
                           ai_process_sm_data_array):
        
        mirror_saved_sampling_frame = self.saved_sampling_frame
        #mirror_saved_sampling_data = 
        # when get new frame, save data into "self.input_data_array"
        if (mirror_saved_sampling_frame > self.sync_saved_sampling_frame):
            self.frame_unit = int(self.SAMPLING_RATE * self.SAMPLING_WINDOW)   # 2205 here
            if (self.sync_saved_sampling_frame == 0):
                self.input_data_array = np.asarray(self.saved_sampling_data_str[0]) / 32768.0
                ai_process_sm_data_array[0 : self.frame_unit] = self.input_data_array[0 : self.frame_unit]
                ai_process_sm_data_array_end.value = self.frame_unit
                self.sync_saved_sampling_frame = 1
                ai_process_sm_data_chunk.value = 1
    
            else:
                frame_difference = mirror_saved_sampling_frame - self.sync_saved_sampling_frame
                for index in range(frame_difference):
                    self.input_data_array = np.hstack((self.input_data_array, 
                                                       np.asarray(self.saved_sampling_data_str[min(mirror_saved_sampling_frame-1,
                                                                                                   len(self.saved_sampling_data_str)-1,
                                                                                                   self.sync_saved_sampling_frame+index)]) / 32768.0))
                    start_frame = int(self.frame_unit * (self.sync_saved_sampling_frame+index))
                    end_frame = start_frame + self.frame_unit
                    if len(ai_process_sm_data_array[start_frame:end_frame]) == len(self.input_data_array[start_frame:end_frame]) :
                        ai_process_sm_data_array[start_frame:end_frame] = self.input_data_array[start_frame:end_frame]
                        ai_process_sm_data_array_end.value = end_frame
                    self.sync_saved_sampling_frame += 1
                    ai_process_sm_data_chunk.value = self.sync_saved_sampling_frame

            #print ("frame sync done")
            pass
            
        else:
            #print ("no frame need to be sync")
            pass


def audio_interface_control(ai_proc_sm_pstop,
                            ai_proc_sm_rec_running,
                            ai_proc_sm_data_chunk,
                            ai_proc_sm_data_chunk_size,
                            ai_proc_sm_data_array_end,
                            ai_proc_sm_data_array
                            ):
    # set recording service
    audio_service = record_service()
    ai_proc_sm_data_chunk_size.value = audio_service.SAMPLING_WINDOW

    # start run recording    
    try :
        audio_service.run_sampling_stream()
    except IOError:
        print ("[audio interface] Microphone is not ready!")
        audio_service.__init__()


    # update chunk status       
    while (ai_proc_sm_pstop.value == 0):
        time.sleep(0.002)
        audio_service.update_frame_array(ai_proc_sm_data_chunk,
                                         ai_proc_sm_data_array_end,
                                         ai_proc_sm_data_array)
        if (ai_proc_sm_data_chunk.value > 0):
            if (ai_proc_sm_rec_running.value == 0):
                ai_proc_sm_rec_running.value = 1
    
    # stop recording
    audio_service.close_sampling_stream()
    audio_service.__init__()
    #audio_service.save_data_2_file()

    print ("[audio interface] sampling string stopped.")



# test program here
if __name__ == '__main__':
    
    samp_rate = 44100
    sm_audio_data_size = samp_rate * 60 * 30   # space for 30 min long audio 
    
    # create sheared memory for audio interface process
    ai_proc_sm_pstop = multiprocessing.Value('i', 0)
    ai_proc_sm_rec_running = multiprocessing.Value('i', 0)
    ai_proc_sm_data_chunk = multiprocessing.Value('i', 0)
    ai_proc_sm_data_chunk_size = multiprocessing.Value('d', 0)
    ai_proc_sm_data_array_end = multiprocessing.Value('i', 0)
    ai_proc_sm_data_array = multiprocessing.Array('d', sm_audio_data_size)
    #ai_process_sm_data_queue = multiprocessing.Queue()

    ai_process_main = multiprocessing.Process(target = audio_interface_control,      \
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


    for i in range(0, 40):
        time.sleep(0.5)
        print (ai_proc_sm_data_chunk.value * ai_proc_sm_data_chunk_size.value)

  
    rec_audio_data = np.array(ai_proc_sm_data_array[0: ai_proc_sm_data_array_end.value])
    
    # check if all data is good
    if (ai_proc_sm_data_chunk.value * ai_proc_sm_data_chunk_size.value * samp_rate == ai_proc_sm_data_array_end.value):
        buffer_is_good = 1
    else:
        buffer_is_good = 0
        
    if buffer_is_good == 1:
        print ("great, no data loss.")
    else:
        print ("sad, some data is missing.")
    


    # save audio data into file    
    save_file_name = "temp.wav"
    save_wave_16bit(rec_audio_data, save_file_name, samp_rate)
    
    # stop Rec process
    ai_proc_sm_pstop.value = 1
    
    


    
    
    
    
    

