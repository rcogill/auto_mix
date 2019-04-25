'''
Mixes can be generated by directly running this script. Useage:

python mix.py --playlist_file FILE.YAML --directory DIR

Here FILE.YAML is a YAML formatted file describing the mix to be generated
and DIR is the directory containing the playlist file and all mp3 files 
to be mixed.
'''

import click
import mix_worker

@click.command()
@click.option('--playlist_file', default=None,\
 help='A YAML file containing information on the playlist to generate.')
@click.option('--directory', default=None,\
 help='The directory where the playlist and audio files are stored.')
#------
def main(playlist_file, directory):
    return mix_worker.create_mix_files(playlist_file, directory)

#---------------------------------------------------------

if __name__ == '__main__':
    main()