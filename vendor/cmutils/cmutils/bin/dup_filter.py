# -*- coding: utf-8 -*-

# Copyright © 2019 by IBPort. All rights reserved.
# @Author: Neal Wong
# @Email: ibprnd@gmail.com

import os
import sys
import io
import csv

import click

from cmutils import logger


@click.command()
@click.option('--i1', help='File to filter.')
@click.option('--i2', help='File that filters against.')
@click.option('--c1', type=int, default=1, help='Column of file 1 to filter, default is 1.')
@click.option('--c2', type=int, default=1, help='Column of file 2 to filter against, default is 1.')
@click.option('--s1', default='\t', help='Separator of file 1, default is tab.')
@click.option('--s2', default='\t', help='Separator of file 2, default is tab.')
@click.option('-v', '--invert_match', is_flag=True, help='Invert match, select non-matching lines.')
@click.option('-o', '--output_path', help='Output file.')
def filter_dup(i1, i2, c1, c2, s1, s2, invert_match, output_path):
    input_path = os.path.abspath(os.path.expanduser(i1))
    file_path = os.path.abspath(os.path.expanduser(i2))
    for f in [input_path, file_path]:
        if not os.path.isfile(f):
            logger.error('File not found - %s!' % f)
            sys.exit(1)

    output_path = os.path.abspath(os.path.expanduser(output_path))
    output_dir = os.path.dirname(output_path)
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            logger.error('Could not create output directory - %s!', output_dir)
            sys.exit(1)

    i_col = c1
    f_col = c2
    i_sep = s1
    f_sep = s2
    records = dict()
    with io.open(file_path, encoding='utf-8', errors='ignore') as fh:
        reader = csv.reader(fh, delimiter=f_sep)
        for parts in reader:
            n_parts = len(parts)
            if n_parts < f_col:
                logger.warning(
                    'Columns are less than expected! Expected: %s, Actual: %s, line: %s',
                    f_col, n_parts, parts)
                continue

            records[parts[f_col - 1]] = None

    if os.path.isfile(output_path):
        os.remove(output_path)

    with io.open(output_path, 'a', encoding='utf-8', errors='ignore') as oh:
        o_writer = csv.writer(oh, delimiter=i_sep)
        with io.open(input_path, encoding='utf-8', errors='ignore') as ih:
            reader = csv.reader(ih, delimiter=i_sep)
            for parts in reader:
                n_parts = len(parts)
                if n_parts < i_col:
                    logger.warning(
                        'Columns are less than expected! Expected: %s, Actual: %s, line: %s',
                        i_col, n_parts, parts)
                    continue

                if invert_match:
                    if parts[i_col - 1] in records:
                        o_writer.writerow(parts)
                else:
                    if parts[i_col - 1] not in records:
                        o_writer.writerow(parts)


if __name__ == '__main__':
    filter_dup()
