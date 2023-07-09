import copy
import unittest
import mock
import os

import denali
from denali.denali_variables import denaliVariables
from denali.denali_types import OutputTarget


class TestOutputFormatting(unittest.TestCase):
    output_formats = ['txt', 'csv', 'json', 'space', 'newline', 'comma',
                      'update', 'yaml',]


    def setUp(self):
        # Ensure that each test run has a fresh instance of denaliVariables.
        denali.denaliVariables = copy.deepcopy(denaliVariables)

    def tearDown(self):
        denali.denaliVariables = None

    def _strip_tmp_file_pid_and_time(self, output_list):
        for item in output_list:
            if item.type == 'csv_file' \
                    and item.filename.startswith('/tmp/denali-tmp'):
                item.filename = '/tmp/denali-tmp.csv'

        return output_list

    def test_prioritizeOutput_adds_tmp_csv_file(self):
        """ Does prioritizeOutput add a tmp csv_file if none is specified? """
        orig = [OutputTarget(type='txt_orig', filename='', append=False),]
        out = denali.prioritizeOutput(denaliVariables, orig)
        self._strip_tmp_file_pid_and_time(out)
        self.assertIn(OutputTarget('csv_file', '/tmp/denali-tmp.csv'), out)

    def test_prioritizeOutput_doesnt_override_existing_csv_file(self):
        orig = [
            OutputTarget(type='txt_screen', filename='', append=False),
            OutputTarget(type='json_screen', filename='', append=False),
            OutputTarget(type='csv_file', filename='foo.csv', append=False)
        ]
        out = denali.prioritizeOutput(denaliVariables, orig)

        self.assertIn(
            OutputTarget(type='csv_file', filename='foo.csv', append=False),
            out)

    def test_prioritizeOutput_moves_csv_file_to_zeroeth_position(self):
        orig = [
            OutputTarget('txt_screen', ''),
            OutputTarget('json_screen', ''),
            OutputTarget('csv_file', 'foo.csv')
        ]
        out = denali.prioritizeOutput(denaliVariables, orig)

        self.assertEqual(OutputTarget('csv_file', 'foo.csv'), out[0])

    def test_prioritizeOutput_preserves_ordering(self):
        """ Does prioritizeOutput keep the ordering of output types except csv_file ? """
        orig = [
                OutputTarget('txt_screen', ''),
                OutputTarget('csv_file', 'foo.csv'),
                OutputTarget('json_screen', ''),
                OutputTarget('yaml_screen', ''),
                OutputTarget('space_screen', '')
        ]
        expected = [
            OutputTarget('csv_file', 'foo.csv'),
            OutputTarget('txt_screen', ''),
            OutputTarget('json_screen', ''),
            OutputTarget('yaml_screen', ''),
            OutputTarget('space_screen', '')
        ]
        out = denali.prioritizeOutput(denaliVariables, orig)

        self.assertEqual(expected, out)

    def test_prioritizeOutput_doesnt_modify_original_list(self):
        """ Does prioritizeOutput return a new list without modifying the input list? """
        orig = [
            OutputTarget('txt_screen', ''),
            OutputTarget('csv_file', 'foo.csv'),
            OutputTarget('json_screen', ''),
            OutputTarget('yaml_screen', ''),
            OutputTarget('space_screen', '')
        ]
        backup = copy.deepcopy(orig)

        self.assertEqual(orig, backup, 'Test setup is broken!')
        out = denali.prioritizeOutput(denaliVariables, orig)
        self.assertEqual(orig, backup, 'prioritizeOutput modified the list passed to it.')

    def test_prioritizeOutput_doesnt_add_tmpfile_if_csv_file_exists_in_input(self):
        """ Does prioritizeOutput unnecessarily modify denaliVariables? """
        backup_tmpfiles = copy.deepcopy(denali.denaliVariables["tmpFilesCreated"])
        out = denali.prioritizeOutput(denaliVariables, 
            [
                OutputTarget('csv_file', 'foo.csv'),
                OutputTarget('txt_screen', '')
            ]
        )
        self.assertEqual(backup_tmpfiles, denali.denaliVariables["tmpFilesCreated"])

    def test_prioritizeOutput_adds_tmpfile_if_it_adds_csv_file(self):
        # Make sure tmpFilesCreated is empty!
        denali.denaliVariables["tmpFilesCreated"] = []
        # This should create a tmpFile in tmpFilesCreated.
        denali.prioritizeOutput(denaliVariables, [OutputTarget('txt_screen', '')])
        self.assertNotEqual([], denaliVariables["tmpFilesCreated"])

    def test_prioritizeOutput_moves_all_csv_files_to_beginning(self):
        """ Does prioritizeOutput move all csv_file entries to the beginning, even if they aren't passed in contiguously? """
        orig = [
            OutputTarget('txt_screen', ''),
            OutputTarget('csv_file', 'foo.csv'),
            OutputTarget('json_screen', ''),
            OutputTarget('csv_file', 'bar.csv'),
        ]
        expected = [
            OutputTarget('csv_file', 'foo.csv'),
            OutputTarget('csv_file', 'bar.csv'),
            OutputTarget('txt_screen', ''),
            OutputTarget('json_screen', '')
        ]

        first_non_csv = 2  # First non-csv_file entry in expected output.

        out = denali.prioritizeOutput(denaliVariables, orig)
        for item in out[:first_non_csv]:
            self.assertEqual(item.type, 'csv_file',
                             "csv_file types aren't all at the beginning.")

        for item in out[first_non_csv:]:
            self.assertNotEqual(item.type, 'csv_file',
                                "Non- csv_file types aren't all at the end.")

    def test_outputTargetDetermination_defaults_to_txt(self):
        out = denali.outputTargetDetermination(denaliVariables, '')
        self.assertIn(OutputTarget('txt_screen', ''), out)

        out = denali.outputTargetDetermination(denaliVariables, 'unknown')
        self.assertIn(OutputTarget('txt_screen', ''), out)

        out = denali.outputTargetDetermination(denaliVariables, 'unknown.filetype')
        self.assertIn(OutputTarget('txt_file', 'unknown.filetype'), out)

    def test_outputTargetDetermination_adds_filetype_for_all_formats(self):
        expected = [OutputTarget(fmt+'_file', 'test.'+fmt)
                    for fmt in self.output_formats]
        param = ','.join(['test.'+fmt for fmt in self.output_formats])

        out = denali.outputTargetDetermination(denaliVariables, param)
        for e in expected:
            self.assertIn(e, out)

    def test_outputTargetDetermination_adds_screentype_for_all_formats(self):
        expected = [OutputTarget(fmt+'_screen', '')
                    for fmt in self.output_formats]
        param = ','.join([fmt for fmt in self.output_formats])

        out = denali.outputTargetDetermination(denaliVariables, param)
        for e in expected:
            self.assertIn(e, out)

    def test_outputTargetDetermination_respects_overwrite_param(self):
        # When there is no file found, it should add the filename it to the output.
        with mock.patch('os.path.isfile', side_effect=lambda f: False):
            out = denali.outputTargetDetermination(denaliVariables, '/tmp/test_file.txt',
                                                   over_write_existing_file=False)
        self.assertIn(OutputTarget('txt_file', '/tmp/test_file.txt'), out)

        with mock.patch('os.path.isfile', side_effect=lambda f: True):
            # File is found and over_write is False. Should not be in the output.
            out = denali.outputTargetDetermination(denaliVariables, '/tmp/test_file.txt',
                                                   over_write_existing_file=False)
            self.assertNotIn(OutputTarget('txt_file', '/tmp/test_file.txt'), out)

            # File is found and over_write is True. Should be in the output.
            out = denali.outputTargetDetermination(denaliVariables, '/tmp/test_file.txt',
                                                   over_write_existing_file=True)
            self.assertIn(OutputTarget('txt_file', '/tmp/test_file.txt'), out)

    @mock.patch('os.path.expanduser', side_effect=lambda s: s.replace('~', '/home/test'))
    def test_outputTargetDetermination_expands_user(self, _mock):
        out = denali.outputTargetDetermination(denaliVariables, '~/foo.txt')
        self.assertIn(OutputTarget('txt_file', '/home/test/foo.txt'), out)

