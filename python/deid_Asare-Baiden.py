import re
import sys
import os
import chardet

phone_pattern = '(\d{3}[-\.\s/]??\d{3}[-\.\s/]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s/]??\d{4})'


# compiling the reg_ex would save some time!
ph_reg = re.compile(phone_pattern)


def check_for_phone(patient, note, chunk, output_handle):
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
        Search the entire chunk for phone number occurances. Find the location of these occurances
        relative to the start of the chunk, and output these to the output_handle file.
        If there are no occurances, only output Patient X Note Y (X and Y are passed in as inputs) in one line.
        Use the precompiled regular expression to find phones.
    """
    # The perl code handles texts a bit differently,
    # we found that adding this offset to start and end positions would produce the same results
    offset = 27

    # For each new note, the first line should be Patient X Note Y and then all the personal information positions
    output_handle.write('Patient {}\tNote {}\n'.format(patient, note))

    # search the whole chunk, and find every position that matches the regular expression
    # for each one write the results: "Start Start END"
    # Also for debugging purposes display on the screen (and don't write to file)
    # the start, end and the actual personal information that we found
    for match in ph_reg.finditer(chunk):

        # debug print, 'end=" "' stops print() from adding a new line
        print(patient, note, end=' ')
        print((match.start()-offset), match.end()-offset, match.group())

        # create the string that we want to write to file ('start start end')
        result = str(match.start()-offset) + ' ' + \
            str(match.start()-offset) + ' ' + str(match.end()-offset)

        # write the result to one line of output
        output_handle.write(result+'\n')


def checking_file_encoding(file_path):
    """
        Detects the encoding of a file.

        Inputs:
            - file_path: The path to the file to be analyzed.

        Returns:
            The detected encoding of the file.
        """
    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read())
    return result['encoding']



def load_string_repository(file_path):
    """
      Loads and processes a string repository from a file.

      Inputs:
          - file_path: The path to the file containing the string repository.

      Returns:
          A list of processed and filtered strings.

      Logic:
          - The function reads the specified file and detects its encoding.
          - It then processes the file's contents to create a list of strings.
          - The list is filtered to include only alphanumeric strings.
          - Strings are converted to lowercase and sorted by length in descending order.
          - Any '|' characters are removed, and strings with a length less than 2 are excluded.


      """
    string_repository = [' ']

    encoding = checking_file_encoding(file_path)
    with open(file_path, 'r', encoding=encoding) as file:
        string_repository.extend([line for line in file.read().split('\n') if line])

    string_repository = [name for name in string_repository if name.isalpha()]
    string_repository = [name.lower() for name in string_repository]
    string_repository.sort(key=len, reverse=True)
    string_repository = [name.replace('|', '') for name in string_repository]
    string_repository = [name for name in string_repository if len(name) > 1]

    return string_repository


def check_for_name(patient_id, note_id, text_chunk, output_handle):
    """
        Searches for names within a text chunk and outputs their positions.

        Inputs:
            - patient_id: The patient number for reference in the output.
            - note_id: The note number for reference in the output.
            - text_chunk: The text chunk (patient note) to search for names.
            - output_handle: An open file handle where results will be written.

        Logic:
            - The function searches for full names within the text chunk.
            - It combines first names and last names from specified files into a list.
            - For each full name in the list, it constructs a regular expression pattern.
            - The function then searches the text chunk using the regular expression pattern.
            - If a name is found, its position and the name itself are printed and written to the output.

        Note:
            - The `output_handle` is used to avoid repeated file open/close operations for efficiency.

        Example:
            - If a full name "John Smith" is found in the text, it will be recorded as:
              "Patient X Note Y: Start Start END" in the output.

        """
    offset = 27
    output_handle.write('Patient {}\tNote {}\n'.format(patient_id, note_id))
    first_names = load_string_repository('../lists/doctor_first_names.txt')
    last_names = load_string_repository('../lists/doctor_last_names.txt')
    fullname = first_names + last_names
    for f in fullname:
        fullname_pattern = r'([A-Z][A-Za-z\'\-]+(?: [A-Z][A-Za-z\'\-]+)*)'.format(f.lower())
        fullname_regex = re.compile(fullname_pattern)
        for match in fullname_regex.finditer(text_chunk):
            name = match.group().strip()
            if len(name) > 1:
                print(patient_id, note_id, end=' ')
                print((match.start()-offset), match.end()-offset, match.group())
                result = str(match.start()-offset) + ' ' + \
                    str(match.start()-offset) + ' ' + str(match.end()-offset)
                output_handle.write(result+'\n')

def get_all_file_paths(directory):
    """
        Retrieves a list of file paths within a directory and its subdirectories.

        Inputs:
            - directory: The root directory to search for files.

        Returns:
            A list of file paths found within the specified directory and its subdirectories.

        Logic:
            - The function uses the `os.walk` function to traverse the directory and its subdirectories.
            - For each file found, the function constructs the full file path.
            - The list of file paths is then returned.

        """

    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list


def deid_phone(text_path='id.text', output_path='name.phi'): # output file is name.phi instead of phone.phi
    """
    Inputs:
        - text_path: path to the file containing patient records
        - output_path: path to the output file.

    Outputs:
        for each patient note, the output file will start by a line declaring the note in the format of:
            Patient X Note Y
        then for each phone number found, it will have another line in the format of:
            start start end
        where the start is the start position of the detected phone number string, and end is the detected
        end position of the string both relative to the start of the patient note.
        If there is no phone number detected in the patient note, only the first line (Patient X Note Y) is printed
        to the output
    Screen Display:
        For each phone number detected, the following information will be displayed on the screen for debugging purposes
        (these will not be written to the output file):
            start end phone_number
        where `start` is the start position of the detected phone number string, and `end` is the detected end position of the string
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
                    # pass all to check_for_phone to find any phone numbers in note.
                    # check_for_phone(patient, note, chunk.strip(), output_file)

                    # calling function to check for names
                    check_for_name(patient, note, chunk.strip(), output_file)


                    # initialize the chunk for the next note to be read
                    chunk = ''


if __name__ == "__main__":

    deid_phone(sys.argv[1], sys.argv[2])