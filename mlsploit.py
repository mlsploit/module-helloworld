from __future__ import print_function

import json
import os


INPUT_DIR = '/mnt/input'
OUTPUT_DIR = '/mnt/output'
INPUT_JSON_PATH = os.path.join(INPUT_DIR, 'input.json')
OUTPUT_JSON_PATH = os.path.join(OUTPUT_DIR, 'output.json')
INPUT_SCHEMA_PATH = './input.schema'
OUTPUT_SCHEMA_PATH = './output.schema'


class _Function(object):
    class _OptionPolicy(object):
        def __init__(self, name, type_, required, values=None):
            self.name = name

            if type_ in ['int', 'str', 'bool', 'float', 'enum']:
                self.type = type_

                if self.type == 'enum':
                    if values is None or type(values) is not list:
                        raise ValueError('Cannot parse "values" '
                                         ' for option policy "%s"' % name)

            else:
                raise ValueError('Unrecognized type "%s" for option policy "%s"'
                                 % (type_, name))

            self.required = bool(required)
            self.values = values or list()

        def verify_value(self, val):
            if val is None and not self.required:
                return True

            elif self.type == 'enum' and val not in self.values:
                    return False

            elif type(val).__name__ != self.type:
                    return False

            return True

        @classmethod
        def parse(cls, data):
            name = data['name']
            type_ = data['type']
            required = data.get('required', False)
            values = data.get('values', None)

            return cls(name, type_, required, values=values)

    class _ExtensionPolicy(object):
        def __init__(self, extension, tags=None):
            self.extension = str(extension)

            tags = tags or dict()
            tags = dict(tags)
            for tag, val in tags.items():
                if type(tag) is not str or type(val) is not str:
                    raise ValueError('Cannot parse tags '
                                     'for extension "%s"' % ext)
            self.tags = tags

        @classmethod
        def parse(cls, data):
            if 'extension' not in data:
                raise ValueError('Cannot parse "%s" as extension' % data)

            ext = data['extension']
            tags = data.get('tags')

            return cls(ext, tags)

    class _RequiredInputTagPolicy(object):
        def __init__(self, tag):
            if type(tag) is not str:
                raise ValueError('Cannot parse "%s" '
                                 'as required input tag policy' % tag)

            self.tag = tag

        @classmethod
        def parse(cls, data):
            return cls(data)

    class _OutputTagPolicy(object):
        def __init__(self, name, type_):
            if type_ not in ['int', 'str', 'bool', 'float']:
                raise ValueError('Unrecognized type '
                                 'for output tag policy "%s"' % name)

            self.name = name
            self.type = type_

        @classmethod
        def parse(cls, data):
            name = data['name']
            type_ = data['type']

            return cls(name, type_)

    def __init__(self, fn_schema_in, fn_schema_out):
        assert fn_schema_out['name'] == fn_schema_in['name']
        self.name = fn_schema_in['name']

        self.option_policies = list(
            map(self._OptionPolicy.parse,
                fn_schema_in['options']))
        self.extension_policies = list(
            map(self._ExtensionPolicy.parse,
                fn_schema_in.get('extensions', list())))
        self.required_input_tag_policies = list(
            map(self._RequiredInputTagPolicy.parse,
                fn_schema_in.get('required_tags', list())))

        self.output_tag_policies = list(
            map(self._OutputTagPolicy.parse,
                fn_schema_out.get('output_tags', list())))
        self.has_modified_files = \
            bool(fn_schema_out.get('has_modified_files', False))
        self.has_extra_files = \
            bool(fn_schema_out.get('has_extra_files', False))

    def __repr__(self):
        return self.name

    @classmethod
    def load_all_from_schema(cls):
        input_schema = json.load(open(INPUT_SCHEMA_PATH, 'r'))
        output_schema = json.load(open(OUTPUT_SCHEMA_PATH, 'r'))

        input_schema = {fn['name']: fn for fn in input_schema['functions']}
        output_schema = {fn['name']: fn for fn in output_schema['functions']}

        functions = list()
        for name in input_schema.keys():
            fn_schema_in = input_schema[name]
            fn_schema_out = output_schema[name]

            functions.append(cls(fn_schema_in, fn_schema_out))

        return functions

    @classmethod
    def load_by_name_from_schema(cls, name):
        input_schema = json.load(open(INPUT_SCHEMA_PATH, 'r'))
        output_schema = json.load(open(OUTPUT_SCHEMA_PATH, 'r'))

        input_schema = {fn['name']: fn for fn in input_schema['functions']}
        output_schema = {fn['name']: fn for fn in output_schema['functions']}

        fn_schema_in = input_schema[name]
        fn_schema_out = output_schema[name]

        return cls(fn_schema_in, fn_schema_out)


class _InputFile(object):
    def __init__(self, path, tags=None):
        assert os.path.exists(path), 'No file found at %s' % path

        tags = tags or dict()
        tags = dict(tags)
        for tag, val in tags.items():
            if type(tag) is not str:
                raise ValueError('Cannot parse tags '
                                 'for input file "%s"' % path)

        self.path = path
        self.tags = tags

    def __repr__(self):
        return self.path

    def has_tag(self, tag):
        return tag in self.tags

    def get_tag(self, tag):
        if self.has_tag(tag):
            return self.tags[tag]

    @property
    def extension(self):
        return os.path.splitext(self.path)[-1][1:]

    def check_extension_policy(self, extension_policy):
        if self.extension != extension_policy.extension:
            return False

        for required_tag, value in extension_policy.tags.items():
            if self.get_tag(required_tag) != value:
                return False

        return True

    def check_required_input_tag_policy(self, required_input_tag_policy):
        return self.has_tag(required_input_tag_policy.tag)


class _OutputFile(_InputFile):
    def __init__(self, path, tags=None, is_modified=False, is_extra=False):
        super(_OutputFile, self).__init__(path, tags=tags)

        assert not (is_modified and is_extra), \
            '"%s" is marked as modified as well as extra'

        self.is_modified = is_modified
        self.is_extra = is_extra

    def check_output_tag_policies(self, output_tag_policies):
        if len(self.tags) == 0:
            return True

        check = True
        for tag, value in self.tags.items():
            check = check and any(
                tag == tag_policy.name
                and type(value).__name__ == tag_policy.type
                for tag_policy in output_tag_policies)

        return check

    def check_modified_file_policy(self, function):
        if self.is_modified:
            return function.has_modified_files

        return True

    def check_extra_file_policy(self, function):
        if self.is_extra:
            return function.has_extra_files

        return True


class Job(object):
    _initialized = False
    _committed = False
    _function_obj = None
    _output_files = list()
    input_json = None
    function = None
    options = None
    input_files = list()

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        input_json = json.load(open(INPUT_JSON_PATH, 'r'))
        function = _Function.load_by_name_from_schema(input_json['name'])
        options = input_json['options']
        num_files = input_json['num_files']
        for i in range(num_files):
            filename = input_json['files'][i]
            path = os.path.join(INPUT_DIR, filename)
            tags = input_json['tags'][i]

            input_file = _InputFile(path, tags)

            assert any(input_file.check_extension_policy(extension_policy)
                       for extension_policy in function.extension_policies), \
                '"%s" does not have the correct extension ' \
                'for the given tags' % filename

            assert all(
                input_file.check_required_input_tag_policy(
                    required_input_tag_policy)
                for required_input_tag_policy
                in function.required_input_tag_policies), \
                '"%s" does not have the required tags' % filename

            cls.input_files.append(input_file)

        cls._function_obj = function
        cls._output_files = list()
        cls.input_json = input_json
        cls.function = function.name
        cls.options = options

        cls._initialized = True

    @classmethod
    def make_output_filepath(cls, filename):
        return os.path.join(OUTPUT_DIR, filename)

    @classmethod
    def add_output_file(cls, path, tags=None,
                        is_modified=False, is_extra=False):

        assert not cls._committed, 'output has already been commited'

        assert os.path.dirname(path) == OUTPUT_DIR, \
            'output files can only be in %s; found %s' % (OUTPUT_DIR, path)

        filename = os.path.basename(path)

        function = cls._function_obj
        output_file = _OutputFile(path, tags=tags,
                                  is_modified=is_modified,
                                  is_extra=is_extra)

        assert output_file.check_output_tag_policies(
            function.output_tag_policies), \
            'tags for output file "%s" are not in the allowed set' % filename

        assert output_file.check_modified_file_policy(function), \
            'output file "%s" cannot be a modified file' % filename

        assert output_file.check_extra_file_policy(function), \
            'output file "%s" cannot be an extra file' % filename

        cls._output_files.append(output_file)

    @classmethod
    def commit_output(cls):
        if cls._committed:
            return

        output_dict = {
            'name': cls.function,
            'files': list(),
            'tags': list(),
            'files_extra': list(),
            'files_modified': list()}

        for output_file in cls._output_files:
            filename = os.path.basename(output_file.path)
            tags = output_file.tags

            output_dict['files'].append(filename)
            output_dict['tags'].append(tags)

            if output_file.is_modified:
                output_dict['files_modified'].append(filename)

            elif output_file.is_extra:
                output_dict['files_extra'].append(filename)

        json.dump(output_dict, open(OUTPUT_JSON_PATH, 'w'))

        cls._committed = True


Job.initialize()

if __name__ == '__main__':
    _Function.load_all_from_schema()
