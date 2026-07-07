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
@click.option('--i1', help='Input file 1.')
@click.option('--i2', help='Input file 2.')
@click.option('--c1', type=int, default=1, help='Join on this field of file 1, default is 1.')
@click.option('--c2', type=int, default=1, help='Join on this field of file 2, default is 1.')
@click.option('--s1', default='\t', help='Separator of file 1, default is tab.')
@click.option('--s2', default='\t', help='Separator of file 2, default is tab.')
@click.option('--so', default='\t', help='Separator of output file, default is tab.')
@click.option('-r', '--reserve_order', is_flag=True, help='Whether reserve line order according to file 1.')
@click.option('-k1', is_flag=True, help='Whether to keep just one joining column.')
@click.option('-o', '--output_path', help='Output file.')
def join_file(i1, i2, c1, c2, s1, s2, so, reserve_order, k1, output_path):
    file1 = os.path.abspath(os.path.expanduser(i1))
    file2 = os.path.abspath(os.path.expanduser(i2))
    for f in [file1, file2]:
        if not os.path.isfile(f):
            logger.error('File not found - %s!', f)
            sys.exit(1)

    output_path = os.path.abspath(os.path.expanduser(output_path))
    output_dir = os.path.dirname(output_path)
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            logger.error('Could not create output directory - %s!', output_dir)
            sys.exit(1)

    records = dict()
    lines_cnt = 0
    with io.open(file1, encoding='utf-8', errors='ignore') as fh:
        reader = csv.reader(fh, delimiter=s1)
        idx = 1
        for parts in reader:
            n_parts = len(parts)
            if n_parts < c1:
                logger.warning(
                    'Columns are less than expected! Expected: %s, Actual: %s, line: %s',
                    c1, n_parts, line)
                continue

            key = parts[c1 - 1]
            if key in records:
                records[key]['data'].append({idx: list(parts)})
            else:
                records[key] = {'mapped': False, 'data': [{idx: list(parts)}]}

            idx += 1
        lines_cnt = idx - 1

    max_col_cnt = 0
    with io.open(file2, encoding='utf-8', errors='ignore') as ih:
        reader = csv.reader(ih, delimiter=s2)
        for parts in reader:
            n_parts = len(parts)
            if n_parts < c2:
                logger.warning(
                    'Columns are less than expected! Expected: %s, Actual: %s, line: %s',
                    c2, n_parts, line)
                continue

            if n_parts > max_col_cnt:
                max_col_cnt = n_parts

            key = parts[c2 - 1]
            if key in records:
                if not records[key]['mapped']:
                    if k1:
                        parts.pop(c2 - 1)
                    records[key]['addition'] = list(parts)
                    records[key]['mapped'] = True

    if os.path.isfile(output_path):
        os.remove(output_path)

    with io.open(output_path, 'a', encoding='utf-8', errors='ignore') as oh:
        o_writer = csv.writer(oh, delimiter=so)
        fake_addition = []
        for i in range(0, max_col_cnt):
            fake_addition.append('')

        if reserve_order:
            lines = dict()

            for items in records.values():
                mapped = items.pop('mapped')
                data = items.pop('data')
                addition = items.pop('addition', fake_addition)
                for item in data:
                    idx, line = item.popitem()
                    line.extend(addition)
                    lines[idx] = so.join(line)

            for idx in range(1, lines_cnt + 1):
                o_writer.writerow(lines[idx])
        else:
            for items in records.values():
                mapped = items.pop('mapped')
                data = items.pop('data')
                addition = items.pop('addition', fake_addition)
                for item in data:
                    _, line = item.popitem()
                    line.extend(addition)
                    o_writer.writerow(line)


if __name__ == '__main__':
    join_file()
