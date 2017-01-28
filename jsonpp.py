#!/usr/bin/env python3

import argparse
import sys
import os
import json
from collections import OrderedDict
from math import isfinite, isnan, isinf

BOLD   = "\x1B[1m"
NORMAL = "\x1B[0m"

DEFAULT_COLOR = "\x1B[39m"
BLACK         = "\x1B[30m"
RED           = "\x1B[31m"
GREEN         = "\x1B[32m"
YELLOW        = "\x1B[33m"
BLUE          = "\x1B[34m"
MAGENTA       = "\x1B[35m"
CYAN          = "\x1B[36m"
LIGHT_GRAY    = "\x1B[37m"
DARK_GRAY     = "\x1B[90m"
LIGHT_RED     = "\x1B[91m"
LIGHT_GREEN   = "\x1B[92m"
LIGHT_YELLOW  = "\x1B[93m"
LIGHT_BLUE    = "\x1B[94m"
LIGHT_MAGENTA = "\x1B[95m"
LIGHT_CYAN    = "\x1B[96m"
WHITE         = "\x1B[97m"

class PlainFormatter:
	__slots__ = 'output',

	def __init__(self):
		self.output = None

	def set_output(self, output):
		self.output = output

	def begin_json(self):
		pass

	def end_json(self):
		pass

	def cdata(self, cdata):
		self.output.write(cdata)

	def begin_string(self):
		pass

	def end_string(self):
		pass

	def escape_sequence(self, escape_sequence):
		self.output.write(escape_sequence)

	def bracket(self, bracket):
		self.output.write(bracket)

	def value(self, value):
		self.output.write(value)

	def delimeter(self, delimeter):
		self.output.write(delimeter)

class TTYFormatter(PlainFormatter):
	__slots__ = ()

	def begin_string(self):
		self.output.write(RED)

	def end_string(self):
		self.output.write(DEFAULT_COLOR)

	def escape_sequence(self, escape_sequence):
		self.output.write(CYAN)
		self.output.write(escape_sequence)
		self.output.write(RED)

	def value(self, value):
		self.output.write(MAGENTA)
		self.output.write(value)
		self.output.write(DEFAULT_COLOR)


NUMBER_TYPES = (int, float)
LIST_TYPES = (tuple, list)
DICT_TYPES = (dict, OrderedDict)

SLASH_CHAR_MAP = {
	'"': '\\"',
	'\\': '\\\\',
	'/': '\\/',
	'\b': '\\b',
	'\f': '\\f',
	'\n': '\\n',
	'\r': '\\r',
	'\t': '\\t'
}

CHAR_MAP = {
	'"': '\\"',
	'\\': '\\\\',
	'\b': '\\b',
	'\f': '\\f',
	'\n': '\\n',
	'\r': '\\r',
	'\t': '\\t'
}

def jsonpp(data, output, indent='\t', formatter=None, escape_slash=False, sort_keys=False):
	char_map = SLASH_CHAR_MAP if escape_slash else CHAR_MAP

	if formatter is None:
		formatter = PlainFormatter()

	formatter.set_output(output)

	def handle(value, indentation):
		if value is None:
			formatter.value('null')

		elif isinstance(value, int):
			formatter.value(repr(value))

		elif isinstance(value, float):
			if isnan(value):
				formatter.value('NaN')
			elif isinf(value):
				if value < 0.0:
					formatter.value('-Infinity')
				else:
					formatter.value('Infinity')
			else:
				formatter.value(repr(value))

		elif isinstance(value, str):
			formatter.begin_string()
			formatter.cdata('"')
			for c in value:
				if c in char_map:
					formatter.escape_sequence(char_map[c])
				else:
					cp = ord(c)
					if cp > 127 or not c.isprintable():
						if cp < 0xFFFF:
							formatter.escape_sequence('\\u%04X' % cp)
						else:
							cp -= 0x10000
							high = (cp >> 10) + 0xD800
							low = (cp % 0x400) + 0xDC00
							formatter.escape_sequence(
								'\\u%04X\\u%04X' % (high, low))
					else:
						formatter.cdata(c)
			formatter.cdata('"')
			formatter.end_string()

		elif isinstance(value, LIST_TYPES):
			sub_indent = indentation + indent
			formatter.bracket('[')
			if value:
				item_indent = '\n' + sub_indent
				it = iter(value)
				formatter.cdata(item_indent)
				handle(next(it), sub_indent)
				for item in it:
					formatter.delimeter(',')
					formatter.cdata(item_indent)
					handle(item, sub_indent)

				formatter.cdata('\n' + indentation)

			formatter.bracket(']')

		elif isinstance(value, DICT_TYPES):
			sub_indent = indentation + indent
			formatter.bracket('{')
			if value:
				item_indent = '\n' + sub_indent
				it = iter(sorted(value)) if sort_keys else iter(value)
				formatter.cdata(item_indent)
				key = next(it)
				val = value[key]

				handle(key, sub_indent)
				formatter.delimeter(':')
				formatter.cdata(' ')
				handle(val, sub_indent)

				for key in it:
					val = value[key]
					formatter.delimeter(',')
					formatter.cdata(item_indent)

					handle(key, sub_indent)
					formatter.delimeter(':')
					formatter.cdata(' ')
					handle(val, sub_indent)

				formatter.cdata('\n' + indentation)

			formatter.bracket('}')

		elif isinstance(value, bool):
			formatter.value('true' if value else 'false')

		else:
			raise ValueError(value)

	handle(data, '')
	formatter.cdata('\n')

def main(args):
	parser = argparse.ArgumentParser()
	parser.set_defaults(
		color=os.isatty(sys.stdout.fileno()),
		indent='\t',
		sort_keys=False,
		escape_slash=False)
	parser.add_argument('--color', action='store_true')
	parser.add_argument('--no-color', action='store_false', dest='color')
	parser.add_argument('--sort-keys', action='store_true')
	parser.add_argument('--escape-slash', action='store_true')
	parser.add_argument('--indent', metavar='STRING')
	parser.add_argument('--spaces', nargs='?', default=4, type=lambda value: ' ' * int(value), dest='indent', metavar='COUNT')
	parser.add_argument('--tabs', nargs='?', default=1, type=lambda value: '\t' * int(value), dest='indent', metavar='COUNT')
	parser.add_argument('files', nargs='*')
	opts = parser.parse_args(args)

	if opts.color:
		formatter = TTYFormatter()
	else:
		formatter = PlainFormatter()

	Dict = dict if opts.sort_keys else OrderedDict

	if opts.files:
		for fname in opts.files:
			with open(fname) as fp:
				data = json.load(fp, object_pairs_hook=Dict)
			jsonpp(data, sys.stdout, indent=opts.indent, sort_keys=opts.sort_keys, escape_slash=opts.escape_slash, formatter=formatter)
	else:
		data = json.load(sys.stdin, object_pairs_hook=Dict)
		jsonpp(data, sys.stdout, indent=opts.indent, sort_keys=opts.sort_keys, escape_slash=opts.escape_slash, formatter=formatter)

if __name__ == '__main__':
	try:
		main(sys.argv[1:])
	except BrokenPipeError:
		pass
	except KeyboardInterrupt:
		print('^C')
