import unittest
from denali import denali_search


class TestSplitLine(unittest.TestCase):
    def test_splits_on_columnWidth_chars(self):
        """ Should be able to have a column of exactly columnWidth size. """
        linewidth = 21
        expected = ['This_is_a_test. This,', # 21 chars long
                    'is_only_a_test.'        # 15 chars long
        ]

        self.assertEqual(linewidth, len(expected[0]))

        lines = denali_search.splitLine(''.join(expected), linewidth)
        self.assertEqual(linewidth, len(lines[0]))
        self.assertEqual(expected, lines)

    def test_splits_on_columnWidth_chars(self):
        """ Should be able to have a column of exactly columnWidth size. """
        linewidth = 21
        expected = ['This_is_a_test. This,', # 21 chars long
                    'is_only_a_test.'        # 15 chars long
        ]

        self.assertEqual(linewidth, len(expected[0]))

        lines = denali_search.splitLine(''.join(expected), linewidth)

        self.assertEqual(linewidth, len(lines[0]))
        self.assertEqual(expected, lines)

    def test_separator_after_split(self):
        """ Should be able to have a column of exactly columnWidth size. """
        linewidth = 5
        expected = ['Words', ',test', 'edher', 'e']

        self.assertEqual(linewidth, len(expected[0]))

        lines = denali_search.splitLine(''.join(expected), linewidth)

        self.assertEqual(linewidth, len(lines[0]))
        self.assertEqual(expected, lines)

    def test_splits_on_space(self):
        expected = ['Thisisaverylongline ',
                    'withonespaceinit.']

        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 5)
        self.assertEqual(expected, lines)

    def test_splits_on_comma(self):
        expected = ['Thisisaverylongline,',
                    'withonecommainit.']
        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_on_slash(self):
        expected = ['Thisisaverylongline/',
                    'withoneslashinit.']
        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_on_period(self):
        expected = ['Thisisaverylongline.',
                    'withoneperiodinit']

        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_on_dash(self):
        expected = ['Thisisaverylongline-',
                    'withonedashinit']

        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_on_underscore(self):
        expected = ['Thisisaverylongline_',
                    'withoneuscoreinit']

        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_on_priority_char_first(self):
        """ Does it split lines on priority characters before secondary chars? """
        expected = ['Shorterline,',
                    'has-secondary.chars']

        lines = denali_search.splitLine(''.join(expected), len(''.join(expected)) - 1)

        self.assertEqual(expected, lines)

    def test_splits_no_special_chars(self):
        """ Does it split in the expected place with no splittable chars? """
        expected = ['Loremipsumdolors',
                    'itametapottamus']

        lines = denali_search.splitLine(''.join(expected), len(expected[0]))

        self.assertEqual(expected, lines)

    def test_generateColumnDataOverflow_each_line_fills_whole_column(self):
        """ Does each line returned from generateColumnDataOverflow fill the whole width of the column? """
        width = 10
        test = ['This is a ',
               'test ',
               'thisisonly',
               'one test.']

        # Add 2 (gutter size) to columnWidth. It's subtracted in the function.
        neededData = {'columnWidth': width + 2, 'columnEnd': 0,
                      'columnDifference': 0, 'columnNumber': 0}

        expected = ['{0: <10}'.format(s) for s in test]
        actual = denali_search.generateColumnDataOverflow(''.join(test),neededData)[0][1:]

        self.assertEqual(actual, expected)
