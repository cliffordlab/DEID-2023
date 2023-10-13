import re
import sys


def process(path):
    # takes in file path at input and reads in contents, returns a list
    with open(path, 'r') as file:
        text = file.read()

    # common filler words being excluded from text 
    excluded_words = ['of', 'the', 'and', 'in', 'to', 'for', 'a', 'an', 'is']

    # Split the text by spaces and new lines and remove non-alphabetic characters
    words = re.findall(r'\b[a-zA-Z]+\b', text)

    # Create a new list excluding the words in the excluded_words list
    filtered_words = [word for word in words if word.lower() not in excluded_words]

    # Print the filtered list of words
    return filtered_words


def read_file(path):
    # takes in file path as an input and reads the contents of the file, splitting it into lines
    # returns a list
    res = []
    with open(path, 'r') as file:
        res = file.read().splitlines()

    return res

def check_for_location(patient, note, chunk, output_handle):
    """
    Inputs:
        - patient: Patient Number, will be printed in each occurance of personal information found
        - note: Note Number, will be printed in each occurance of personal information found
        - chunk: one whole record of a patient
        - output_handle: an opened file handle. The results will be written to this file.
            to avoid the time intensive operation of opening and closing the file multiple times
            during the de-identification process, the file is opened beforehand and the handle is passed
            to this function.
    Logic:
        Search the entire chunk for 'location' occurances. Find the location of these occurances
        relative to the start of the chunk, and output these to the output_handle file.
        If there are no occurances, only output Patient X Note Y (X and Y are passed in as inputs) in one line.
        Uses the local_unambig, local_ambig text files precompiled into regular expressions to find locations (ie: towns, cities, hospitals, states).
    """
    # The perl code handles texts a bit differently,
    # we found that adding this offset to start and end positions would produce the same results
    offset = 27

    # For each new note, the first line should be Patient X Note Y and then all the personal information positions
    output_handle.write('Patient {}\tNote {}\n'.format(patient, note))\
    
    # read in location-related text files, returns lists
    location_unambig = read_file("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/locations_unambig.txt")
    local_unambig = read_file("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/local_places_unambig.txt")
    local_ambig = read_file("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/local_places_ambig.txt")
    
    # Read in location-related text files and filters out filler words/whitespace, returns lists
    us_states = process("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/us_states.txt")
    location_ambig = process("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/locations_ambig.txt")
    hospital =  process("/home/suzannealexander/emory/bmi 500/HW8/Alexander_BMI500_deid_2023/lists/stripped_hospitals.txt")

    # combine the lists into a single location list
    location = local_unambig + local_ambig + hospital + us_states + location_ambig + location_unambig

    # join 'location' list elements into a single regex pattern
    pattern = '|'.join(re.escape(loc) for loc in location)

    # compile the regex pattern, with the ignorecase flag (some locations might not have the same casing)
    regex = re.compile(pattern,re.IGNORECASE)

    # compile a regex pattern for locations
    location_reg = re.compile(regex)

    # search the whole chunk, and find every position that matches the regular expression
    # for each one write the results: "Start Start END"
    # Also for debugging purposes display on the screen (and don't write to file)
    # the start, end and the actual personal information that we found
    for match in location_reg.finditer(chunk):
            
        # debug print, 'end=" "' stops print() from adding a new line
        print(patient, note, end=' ')
        print((match.start()-offset), match.end()-offset, match.group())

        # create the string that we want to write to file ('start start end')
        result = str(match.start()-offset) + ' ' + \
            str(match.start()-offset) + ' ' + str(match.end()-offset)

        # write the result to one line of output
        output_handle.write(result+'\n')


def deid_location(text_path='id.text', output_path='location.phi'):
    """
    Inputs:
        - text_path: path to the file containing patient records
        - output_path: path to the output file.
    Outputs:
        for each patient note, the output file will start by a line declaring the note in the format of:
            Patient X Note Y
        then for each location found, it will have another line in the format of:
            start start end
        where the start is the start position of the detected location string, and end is the detected
        end position of the string both relative to the start of the patient note.
        If there is no location detected in the patient note, only the first line (Patient X Note Y) is printed
        to the output
    Screen Display:
        For each location detected, the following information will be displayed on the screen for debugging purposes
        (these will not be written to the output file):
            start end phone_number
        where `start` is the start position of the detected location string, and `end` is the detected end position of the string
        both relative to the start of patient note.
    """
    # start of each note has the patter: START_OF_RECORD=PATIENT||||NOTE||||
    # where PATIENT is the patient number and NOTE is the note number.
    start_of_record_pattern = '^start_of_record=(\d+)\|\|\|\|(\d+)\|\|\|\|$'

    # end of each note has the patter: ||||END_OF_RECORD
    end_of_record_pattern = '\|\|\|\|END_OF_RECORD$'

    # open the output file just once to save time on the time intensive IO
    with open(output_path, 'w+') as output_file:
        with open(text_path) as text:
            # initilize an empty chunk. Go through the input file line by line
            # whenever we see the start_of_record pattern, note patient and note numbers and start
            # adding everything to the 'chunk' until we see the end_of_record.
            chunk = ''
            for line in text:
                record_start = re.findall(
                    start_of_record_pattern, line, flags=re.IGNORECASE)
                if len(record_start):
                    patient, note = record_start[0]
                chunk += line

                # check to see if we have seen the end of one note
                record_end = re.findall(
                    end_of_record_pattern, line, flags=re.IGNORECASE)

                if len(record_end):
                    # Now we have a full patient note stored in `chunk`, along with patient numerb and note number
                    # pass all to check_for_phone to find any locations in note.
                    # check_for_phone(patient, note, chunk.strip(), output_file)
                    check_for_location(patient, note, chunk.strip(), output_file)

                    # initialize the chunk for the next note to be read
                    chunk = ''


if __name__ == "__main__":

    deid_location(sys.argv[1], sys.argv[2])