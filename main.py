from mlsploit import Job


# Initialize the job, which will
# load and verify all input parameters
Job.initialize()

# The job has the following data members
# which is all that is required for running the function
input_json = Job.input_json  # this is a dict for input.json
function = Job.function  # this is the function name
options = Job.options  # this is a dict of the arguments for the function
input_files = Job.input_files  # this is a list of InputFile objects

"""
Each instance in Job.input_files has the following members:
- .path [is the filepath of the input file on disk]
- .tags [is a dict of all tags]
- .has_tag(tag) [returns True if .tags has the `tag` key]
- .get_tag(tag) [returns the value for the `tag` key if present, or None]

A utility function that is helpful for quickly getting the file path on
disk where an output file should be stored is the following:
```
Job.make_output_filepath(filename)
```
Use this path only for writing the output files.

After completing the function and writing the output files to disk, 
you need to call:
```
Job.add_output_file(path, tags=None,
                    is_modified=False, is_extra=False)
```
for each output file, where,
- path [is full file path of the output file located in /mnt/output]
- tags [is a dict of the new tags for the output file]
- is_modified [True if file is modified/transformed version of an input file]
- is_extra [True if file is a new artifact produced by the function]

After adding all output files with the appropriate parameters,
you need to finally call:
```
Job.commit_output()
```
which will create the output.json appropriately
"""

print('Running %s function...' % function)
if function == 'say_hello':
    print('Options: %s' % str(options))
    age = options['age']
    gender = options['gender']
    wears_glasses = options['wears_glasses']

    for input_file in Job.input_files:
        print('Processing %s...' % input_file.path)
        f = open(input_file.path, 'r')
        name = f.readline().strip(' \n')

        message = 'Hello %s' % name
        output_filepath = Job.make_output_filepath('greetings.txt')
        open(output_filepath, 'w').writelines([message])
        print(message)

        tags = {'age': age}

        Job.add_output_file(output_filepath, tags=tags, is_extra=True)
        Job.commit_output()

elif function == 'add_number':
    # TODO
    pass
