'''
This script contains functions that will generate a single, continuous
cross-faded mix from a collection of given input files.

The input mp3 files must be provided together with a playlist file that
specifies the tracks as well as the mix entry and exit points for each.

The resulting mix is saved as a collection of mp3 files that can be
played back-to-back.
'''

import logging
import datetime
import subprocess
import struct
import wave
import zipfile
import os

import yaml

#---------------------------------------------------------

def generate_mix(in_filename, tmp_dir):
    '''Generate the mix from an input archive

    Inputs:
    - in_filename : The name of the zip archive that contains
        the playlist data and audio files
    - tmp_dir : Temporary directory where the archive is placed
        and the ouput archive will be written
    Returns: The name of the zip archive that contains the mixed 
        output audio files
    '''

    # Unzip the input archive to the temp directory
    full_in_fname = os.path.join(tmp_dir, in_filename)
    zp = zipfile.ZipFile(full_in_fname, 'r')
    zp.extractall(tmp_dir)
    zp.close()

    # Generate the mix files according to the provided playlist
    create_mix_files('playlist.yaml', tmp_dir)

    # Place output files in the output archive, zip, and return
    out_filename = 'output_'+in_filename
    full_out_fname = os.path.join(tmp_dir, out_filename)
    zp = zipfile.ZipFile(full_out_fname, 'w', zipfile.ZIP_DEFLATED)
    for filename in os.listdir(tmp_dir):
        if 'M_' in filename:
            zp.write(os.path.join(tmp_dir, filename), arcname=filename)
    zp.close()

    return out_filename

#---------------------------------------------------------

def hms_to_sec(hms):
    '''Convert H:M:S format to total seconds

    Inputs:
    - hms: String formatted as H:M:S with decimal seconds
    Returns: Time in seconds corresponding to the input
    '''

    if '.' not in hms:
        hms = hms + '.0'

    t0 = datetime.datetime.strptime('00:00:00.0', '%H:%M:%S.%f')
    t1 = datetime.datetime.strptime(hms, '%H:%M:%S.%f')
    return (t1-t0).total_seconds()

#---------------------------------------------------------

def sec_to_hms(sec):
    '''Convert total seconds to H:M:S format

    Inputs:
    - sec : Total seconds
    Returns: Total seconds from input formatted as H:M:S
    '''

    return str(datetime.timedelta(seconds=sec))

#---------------------------------------------------------

def write_output(fname, wav_data):
    '''Write raw wav data to an mp3 file. Assumes 16-bit stereo data 
       sampled at 44.1kHz

    Inputs:
    - fname : The name of the output file to write
    - wav_data : Raw wav data to transcode in an mp3 file
    Returns: True if successful
    '''

    # Stereo wav data should be an even number of bytes
    # Chop one off if not
    if len(wav_data)%2 == 1:
        wav_data = wav_data[:-1]

    # Create a temporary wav file before transcoding
    wavef = wave.open('temp.wav', 'w')
    wavef.setnchannels(2) 
    wavef.setsampwidth(2) 
    wavef.setframerate(44100)

    # Write wav data to the file
    for i in range(0, len(wav_data), 2):
        l = int(wav_data[i])
        r = int(wav_data[i+1])
        wavef.writeframesraw(struct.pack('<hh', l, r))
    wavef.writeframes(b'')
    wavef.close()

    # Use ffmpeg to transcode the wav data
    ffmpeg_cmd = ['ffmpeg', '-loglevel', 'quiet', '-y', '-i', 'temp.wav', '-ar',\
        '44100', '-ac', '2', '-b:a', '192k', '-f', 'mp3', fname]
    p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE)
    term_out = p.communicate()[0]

    return True

#---------------------------------------------------------

def mix(v1, v2):
    '''Crossfade to segments of audio. Just uses a simple linear crossfade.

    Inputs:
    - v1 : First array containing raw audio data
    - v2 : Second array containing raw audio data
    Returns: Array containing blended audio data
    '''
    
    # Loop over the arrays and fade
    # Truncate to the minimum length of the two
    N = min(len(v1), len(v2))
    v = []
    for i in range(0, N):
        a = float(i)/N
        v.append(int((1.0-a)*v1[i] + a*v2[i]))
    
    return v
    
#---------------------------------------------------------

def get_section(filename, start, stop, speed):
    '''Extract a segment of wav data from an mp3 file

    Inputs:
    - filename : Name of the input mp3 file
    - start : Starting time of the segment to extract
    - stop : Ending time of the segment to extract
    - speed : Speed adjustment to apply to the extracted segment
    Returns: A dictionary containing the result status, together with
        the extracted audio data
    '''

    # Set a default response of no success, no data extracted
    result = {'success':False, 'data':[]}

    # Construct the ffmpeg command
    atempo = str(speed)
    if stop is None:
        ffmpeg_cmd_1 = ['ffmpeg', '-loglevel', 'quiet', '-i', filename, '-ac', '2', '-ab',\
            '16000', '-ar', '44100', '-ss', start, '-f', 'wav', 'pipe:1']
    else:
        ffmpeg_cmd_1 = ['ffmpeg', '-loglevel', 'quiet', '-i', filename, '-ac', '2', '-ab',\
            '16000', '-ar', '44100', '-ss', start, '-to', stop, '-f', 'wav', 'pipe:1']
    ffmpeg_cmd_2 = ['ffmpeg', '-loglevel', 'quiet', '-i', 'pipe:0', '-af',\
        'atempo='+atempo, '-f', 'wav', 'pipe:1']

    # Run ffmpeg and get a list representation of the audio chunk
    # This pipes two connands together: One to extract the segment and
    # one to adjust the speed
    p1 = subprocess.Popen(ffmpeg_cmd_1, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(ffmpeg_cmd_2, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    wavdata = p2.communicate()[0]
    snd_data = list(struct.unpack('h'*int(len(wavdata)/2), wavdata))

    # try to prevent an audible click at the transition
    for i in range(0, 500):
        snd_data[i] = (float(i)/500)*snd_data[i]
        snd_data[-1-i] = (float(i)/500)*snd_data[-1-i]

    # If successful, return a True success and the extracted audio data
    result['success'] = True
    result['data'] = snd_data

    return result

#---------------------------------------------------------
        
def get_mix_section(c1, c2, r, directory):
    '''Extract a segment of wav data from two mp3 files and
    perform a linear crossfade from the first to the second.

    Inputs:
    - c1 : Dictionary containing the filename and mix entry/exit
      times for the first file.
    - c2 : Dictionary containing the filename and mix entry/exit
      times for the second file.
    - r : Initial speed adjustment to apply to the first section.
    - directory : The directory containing the input mp3 files.
    Returns: A dictionary containing the cross-faded audio data,
      a flag indicating success of the operation, and additional 
      information on the mix entry/exit points and speed.
    '''

    # Initialize the dictionary that will be returned
    result = {'success':False, 's1':None, 'e1':None,\
              's2':None, 'e2':None, 'r':r, 'data':[]}

    # Try to extract the mix entry/exit points for track 1
    try:
        b1 = int(c1['mix_out']['beats'])
        s1 = c1['mix_out']['start']
        e1 = c1['mix_out']['end']
        s1_sec = hms_to_sec(s1)
        e1_sec = hms_to_sec(e1)
    except:
        msg = 'Error processing section 1'
        logging.info(msg)
        return result

    # Store the entry/exit points in the result
    result['s1'] = s1
    result['e1'] = e1

    # Try to extract the mix entry/exit points for track 2        
    try:
        b2 = int(c2['mix_in']['beats'])
        s2 = c2['mix_in']['start']
        e2 = c2['mix_in']['end']
        s2_sec = hms_to_sec(s2)
        e2_sec = hms_to_sec(e2)
    except:
        msg = 'Error processing section 2'
        logging.info(msg)
        return result

    # Store the entry/exit points in the result
    result['s2'] = s2
    result['e2'] = e2

    # If the number of beats differ in the two sections to mix,
    # select the minimum number of beats and adjust entry/exit points
    if b1 != b2:
        b = float(min(b1, b2))
        s1_sec = (1 - b/b1)*e1_sec + (b/b1)*s1_sec
        s1 = sec_to_hms(s1_sec)
        s2_sec = (1 - b/b2)*e2_sec + (b/b2)*s2_sec
        s2 = sec_to_hms(s2_sec)
        result['s1'] = s1
        result['s2'] = s2

    # Extract audio data for the first track
    # Adjust the speed to match the previous mix
    try:
        result_1 = get_section(os.path.join(directory, c1['track']), s1, e1, r)
    except:
        msg = 'Error processing section 1'
        logging.info(msg)
        return result

    # Extract audio data for the second track
    # Adjust the speed to match the tempo of the first track
    try:
        r = r*(e2_sec-s2_sec)/(e1_sec-s1_sec)
        result['r'] = r
        result_2 = get_section(os.path.join(directory, c2['track']), s2, e2, r)
    except:
        msg = 'Error processing section 2'
        logging.info(msg)
        return result

    # Generate the cross-faded audio data
    try:
        v1 = result_1['data']
        v2 = result_2['data']
        v = mix(v1, v2)
    except:
        msg = 'Error generating mix section'
        logging.info(msg)
        return result
        
    result['data'] = v
    result['success'] = True
        
    return result
        
#---------------------------------------------------------

def create_mix_files(playlist_file, directory):
    '''Create a collection of audio files that compose a single,
       continuous mix.

    Inputs:
    - playlist_file : A YAML-formatted input file describing the 
      desired mix.
    - directory : The directory containing the input mp3 files
      and where the output files will be written.
    Returns: True if completed successfully
    '''

    # Generate the log file for this mix job
    logging.basicConfig(filename='mix.log', level=logging.INFO)

    # Open the YAML file contianing playlist file
    try:
        f = open(os.path.join(directory, playlist_file), 'r')
        conf = yaml.load(f.read())
        f.close()
    except:
        msg = 'You must provide a valid YAML file containing the mix playlist'
        logging.info(msg)
        return False

    if len(conf) < 2:
        msg = 'The playlist file must contain at least two tracks'
        logging.info(msg)
        return False

    # Loop over tracks in the playlist, creating new tracks for each
    # Eack track file created contains the mix section at the end

    r = 1.0
    from_start = True
    for i in range(len(conf)-1):
    
        # Get the starting point of the current track
        # In general, the starting point of the current track is the 
        # point where the crossfade completes. 
        # If this is not specified, start from the beginning.
        if from_start is True:
            s = '00:00:00.0'
        else:
            try:
                s = conf[i]['mix_in']['end']
            except:
                msg = 'Missing start time'
                logging.info(msg)
                s = '00:00:00.0'

        # Generate the section of audio containing the cross-fade between
        # this track and the next
        mix_res = get_mix_section(conf[i], conf[i+1], r, directory)
        
        # If the cross-fade was successfully generated, get the section of
        # audio prior to theh cross-fade and append the two sections
        if mix_res['success'] is True:
            e = mix_res['s1']
            main_res = get_section(os.path.join(directory, conf[i]['track']), s, e, r)
            if main_res['success'] is True:
                v = main_res['data'] + mix_res['data']
                from_start = False
            else:
                from_start = True
                continue
        # Otherwise, get all audio up to the end of the track and prepare to 
        # start the new track from the beginning
        else:
            e = None
            main_res = get_section(os.path.join(directory, conf[i]['track']), s, e, r)
            if main_res['success'] is True:
                v = main_res['data']
                from_start = True
            else:
                from_start = True
                continue
        r = mix_res['r']

        # write the resulting mp3 file
        write_output(os.path.join(directory, 'M_'+conf[i]['track']), v)

    # Generate the audio for the last track
    if from_start is True:
        s = '00:00:00.0'
    else:
        try:
            s = conf[-1]['mix_in']['end']
        except:
            msg = 'Missing start time'
            logging.info(msg)
            s = '00:00:00.0'
    e = None
    main_res = get_section(os.path.join(directory, conf[-1]['track']), s, e, r)
    if main_res['success'] is True:
        v = main_res['data']
        from_start = True
        write_output(os.path.join(directory, 'M_'+conf[-1]['track']), v)

    return True

#---------------------------------------------------------