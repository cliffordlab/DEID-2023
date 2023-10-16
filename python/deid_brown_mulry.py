import re
import sys


def check_for_phone_number(patient, note, chunk, output_handle, re_pattern):
    """
    Inputs:
        - patient: Patient Number, will be printed in each occurance of personal information found
        - note: Note Number, will be printed in each occurance of personal information found
        - chunk: one whole record of a patient
        - output_handle: an opened file handle. The results will be written to this file.
            to avoid the time intensive operation of opening and closing the file multiple times
            during the de-identification process, the file is opened beforehand and the handle is passed
            to this function. 
        - re_pattern: pre-compiled pattern to search for
    Logic:
        Search the entire chunk for phone number occurances. Find the location of these occurances 
        relative to the start of the chunk, and output these to the output_handle file. 
        If there are no occurances, only output Patient X Note Y (X and Y are passed in as inputs) in one line.
        Use the precompiled regular expression to find phones.
    """
    # The perl code handles texts a bit differently, 
    # we found that adding this offset to start and end positions would produce the same results
    offset = 27

    # For each new note, the first line should be Patient X Note Y and then all the personal information positions
    output_handle.write('Patient {}\tNote {}\n'.format(patient,note))

    # search the whole chunk, and find every position that matches the regular expression
    # for each one write the results: "Start Start END"
    # Also for debugging purposes display on the screen (and don't write to file) 
    # the start, end and the actual personal information that we found
    for match in re_pattern.finditer(chunk):
                
            # debug print, 'end=" "' stops print() from adding a new line
            print(patient, note, end=' ')
            print((match.start()-offset), match.end()-offset, match.group())
                
            start_idx = str(match.start()-offset)
            end_idx = str(match.end()-offset) 
            result =  f"{start_idx} {start_idx} {end_idx}" 
            
            # write the result to one line of output
            output_handle.write(result+'\n')


def check_for_age(patient, note, chunk, output_handle, re_pattern):
    """
    Inputs:
        - patient: Patient Number, will be printed in each 
            occurance of personal information found.
        - note: Note Number, will be printed in each occurance 
            of personal information found.
        - chunk: one whole record of a patient
        - output_handle: an opened file handle. The results will 
            be written to this file. to avoid the time intensive 
            operation of opening and closing the file multiple times
            during the de-identification process, the file is opened 
            beforehand and the handle is passed to this function. 
        - re_pattern: pre-compiled pattern to search for
    Logic:
        Search the entire chunk for age occurrences. Each age 
        occurence is a sequence of 1-3 numbers followed by a 
        phrase like 'yo' or 'y.o.' or 'years old' etc. The 
        regular expression matches the full phrase but only 
        returns the numbers in the matched age to mimic the 
        format of the id-phi.phrase file. Determines the 
        location of these occurrences relative to the start 
        of the chunk, and output these to the output_handle 
        file. If there are no occurances, only output Patient 
        X Note Y (X and Y are passed in as inputs) in one line.
    """
    # The perl code handles texts a bit differently, 
    # we found that adding this offset to start and end 
    # positions would produce the same results. from 
    # testing i found the offset from this function to 
    # be universally 2 indexes too high so i increased 
    # it from 27 to 29
    offset = 29

    # For each new note, the first line should be 
    # Patient X Note Y and then all the personal 
    # information positions
    output_handle.write('Patient {}\tNote {}\n'.format(patient,note))

    # search the whole chunk, and find every position 
    # that matches the regular expression for each one 
    # write the results: "Start Start END". also, for 
    # debugging purposes display on the screen (and 
    # don't write to file) the start, end and the 
    # actual personal information that we found
    for match in re_pattern.finditer(chunk):
        # extract the numbers from the matched string and convert it to an integer
        age = int(match.group())
        
        # if age is less than 89, skip it
        if age <= 89:
            continue
            
        # debug print, 'end=" "' stops print() from adding a new line
        print(patient, note, end=' ')
        print((match.start()-offset), match.end()-offset, match.group())
            
        # create the string that we want to write to file ('start start end') 
        start_idx = str(match.start()-offset)
        end_idx = str(match.end()-offset) 
        result =  f"{start_idx} {start_idx} {end_idx}"
        
        # write the result to one line of output
        output_handle.write(result+'\n')


def deid_attrs(text_path= 'id.text', id_affix = '_brown_mulry'):
    """
    added function to identify patient ages and de-identify them. uses the core
    from the deid_phone function. the 'output_path' variable isn't being used 
    since we have multiple output files now.

    Inputs:
        text_path: contains the path for the target text to de-identify
        id_affix: string to affix to the end of the output files (to distinguish
        them from others)
    """

    # define our regular expressions
    # moved these here so the ownership of these variables is clearer
    phone_pattern = r'(\d{3}[-\.\s/]??\d{3}[-\.\s/]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s/]??\d{4})'
    # our age pattern is formatted so it only includes the years in the age phrase
    # in the resulting match objects
    age_pattern = r'(?<=\b)(\d{1,3})(?=\s*(yo|y\.?o\.?|yrs\.?\s*old|year\s*old|years\s*old)\b)'

    # precompile regular expressions
    phone_pattern_comp = re.compile(phone_pattern)
    age_pattern_comp = re.compile(age_pattern, re.IGNORECASE)

    # build lists
    output_file_list = [f'phone{id_affix}.phi', f'age{id_affix}.phi']
    attr_check_func_list = [check_for_phone_number, check_for_age]
    pattern_comp_list = [phone_pattern_comp, age_pattern_comp]

    # zip these lists together so we can iterate over them
    comb_attr_list = zip(
        output_file_list, 
        attr_check_func_list, 
        pattern_comp_list
    )

    # start of each note has the patter: START_OF_RECORD=PATIENT||||NOTE||||
    # where PATIENT is the patient number and NOTE is the note number.
    start_of_record_pattern = '^start_of_record=(\d+)\|\|\|\|(\d+)\|\|\|\|$'

    # end of each note has the patter: ||||END_OF_RECORD
    end_of_record_pattern = '\|\|\|\|END_OF_RECORD$'

    # iterate over combined attributes
    for output_path, attr_check_func, re_pattern in comb_attr_list:
        # open the output file just once to save time on the time intensive IO
        with open(output_path,'w+') as output_file:
            with open(text_path) as text:
                # initialize an empty chunk. Go through the input file 
                # line by line whenever we see the start_of_record pattern, 
                # note patient and note numbers and start adding everything 
                # to the 'chunk' until we see the end_of_record.
                chunk = ''
                for line in text:
                    record_start = re.findall(
                        start_of_record_pattern, 
                        line, 
                        flags=re.IGNORECASE
                    )
                    if len(record_start):
                        patient, note = record_start[0]
                    chunk += line

                    # check to see if we have seen the end of one note
                    record_end = re.findall(
                        end_of_record_pattern, 
                        line, 
                        flags=re.IGNORECASE
                    )

                    if len(record_end):
                        # Now we have a full patient note stored in `chunk`, 
                        # along with patient numerb and note number
                        # pass all to the current attr_check_func to 
                        # find any attribute occurences
                        attr_check_func(
                            patient, 
                            note, 
                            chunk.strip(), 
                            output_file, 
                            re_pattern
                        )
                        
                        # initialize the chunk for the next note to be read
                        chunk = ''
                
if __name__== "__main__":
    deid_attrs() # sys.argv[1])
    # deid_attrs('./id.text')
    